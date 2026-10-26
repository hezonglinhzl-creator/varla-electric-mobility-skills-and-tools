[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [switch]$NoBrowser,
    [switch]$ForceRuntime,
    [ValidateRange(5, 120)]
    [int]$WaitSeconds = 60
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$statusUrl = "http://127.0.0.1:8791/api/status"
$webUrl = "http://127.0.0.1:8791/"
$requirementsLock = Join-Path $ProjectRoot "requirements.lock"
$runtimeVerifier = Join-Path $PSScriptRoot "verify_runtime.py"
$timeoutRunner = Join-Path $PSScriptRoot "run_with_timeout.py"
$buildInfoModule = Join-Path $ProjectRoot "app\build_info.py"

foreach ($requiredFile in @($requirementsLock, $runtimeVerifier, $timeoutRunner, $buildInfoModule)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required launcher file is unavailable: $(Split-Path -Leaf $requiredFile)"
    }
}
$buildInfoText = Get-Content -LiteralPath $buildInfoModule -Raw -Encoding UTF8
$buildMatch = [regex]::Match($buildInfoText, '(?m)^BUILD_ID = "([^"\r\n]+)"\s*$')
if (-not $buildMatch.Success) {
    throw "Build identity is invalid."
}
$buildId = $buildMatch.Groups[1].Value
$normalizedProject = $ProjectRoot.TrimEnd("\", "/").ToLowerInvariant()
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $identityBytes = [System.Text.Encoding]::UTF8.GetBytes($normalizedProject)
    $instanceId = ([System.BitConverter]::ToString($sha256.ComputeHash($identityBytes))).Replace("-", "").ToLowerInvariant()
}
finally {
    $sha256.Dispose()
}

function Get-CommandCenterStatus {
    try {
        return Invoke-RestMethod -Uri $statusUrl -Method Get -TimeoutSec 2
    }
    catch {
        return $null
    }
}

function Test-CommandCenterStatus {
    param([object]$Status)
    if ($null -eq $Status) {
        return $false
    }
    $names = @($Status.PSObject.Properties.Name)
    foreach ($requiredName in @("build_id", "instance_id", "bind_host", "bind_port", "local_only", "manual_mode", "auto_mode")) {
        if ($requiredName -notin $names) {
            return $false
        }
    }
    return (
        $Status.build_id -eq $buildId -and
        $Status.instance_id -eq $instanceId -and
        $Status.bind_host -eq "127.0.0.1" -and
        [int]$Status.bind_port -eq 8791 -and
        $Status.local_only -eq $true -and
        $Status.manual_mode -eq $true -and
        $Status.auto_mode -eq $false
    )
}

function Test-CommandCenterPage {
    try {
        $response = Invoke-WebRequest -Uri $webUrl -Method Get -TimeoutSec 2 -UseBasicParsing
        return (
            $response.StatusCode -eq 200 -and
            $response.Content -match 'data-app-id="varla-kol-command-center"'
        )
    }
    catch {
        return $false
    }
}

function Test-LocalPort {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $asyncResult = $client.BeginConnect("127.0.0.1", 8791, $null, $null)
        return $asyncResult.AsyncWaitHandle.WaitOne(500, $false) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

$existingStatus = Get-CommandCenterStatus
if ((Test-CommandCenterStatus $existingStatus) -and (Test-CommandCenterPage)) {
    if (-not $NoBrowser) {
        Start-Process $webUrl | Out-Null
    }
    Write-Output "START_OK"
    Write-Output "reused=true"
    Write-Output "build_id=$buildId"
    Write-Output "instance_id=$instanceId"
    Write-Output "url=$webUrl"
    exit 0
}
if (Test-LocalPort) {
    throw "Port 8791 is occupied by another service. No process was stopped or opened."
}

if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw "LOCALAPPDATA is unavailable."
}
$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path -LiteralPath $bundledPython -PathType Leaf)) {
    throw "Bundled Python runtime is unavailable."
}

function Test-PythonRuntime {
    param([string]$PythonPath)
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        return $false
    }
    & $bundledPython $timeoutRunner --timeout 45 --quiet -- $PythonPath $runtimeVerifier --lock $requirementsLock --project-root $ProjectRoot
    return $LASTEXITCODE -eq 0
}

$dataRoot = Join-Path $env:LOCALAPPDATA "VarlaKOLCommandCenter"
$runtimeRoot = Join-Path $dataRoot "runtime"
$runtimeVenv = Join-Path $runtimeRoot "venv"
$logsRoot = Join-Path $dataRoot "logs"
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
New-Item -ItemType Directory -Path $logsRoot -Force | Out-Null

$projectPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$pythonPath = $null
if ((-not $ForceRuntime) -and (Test-PythonRuntime $projectPython)) {
    $pythonPath = $projectPython
}
else {
    $runtimePython = Join-Path $runtimeVenv "Scripts\python.exe"
    if (-not (Test-PythonRuntime $runtimePython)) {
        Write-Output "Preparing or repairing the locked local runtime..."
        if (-not (Test-Path -LiteralPath $runtimePython -PathType Leaf)) {
            & $bundledPython $timeoutRunner --timeout 120 -- $bundledPython -m venv $runtimeVenv
            if ($LASTEXITCODE -ne 0) {
                throw "Could not create the local runtime within 120 seconds."
            }
        }
        & $bundledPython $timeoutRunner --timeout 180 -- $runtimePython -m pip install --disable-pip-version-check --no-input --require-hashes -r $requirementsLock
        if ($LASTEXITCODE -ne 0) {
            throw "Locked dependency installation failed or exceeded 180 seconds."
        }
        & $bundledPython $timeoutRunner --timeout 120 -- $runtimePython -m pip install --disable-pip-version-check --no-input --no-deps --no-build-isolation -e $ProjectRoot
        if ($LASTEXITCODE -ne 0) {
            throw "Editable project installation failed or exceeded 120 seconds."
        }
    }
    if (-not (Test-PythonRuntime $runtimePython)) {
        throw "The local runtime failed import, exact-version, or pip check verification."
    }
    $pythonPath = $runtimePython
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stdoutLog = Join-Path $logsRoot "server-$timestamp.out.log"
$stderrLog = Join-Path $logsRoot "server-$timestamp.err.log"
$arguments = @(
    "-m",
    "uvicorn",
    "app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8791",
    "--no-access-log"
)
$previousInstanceId = [Environment]::GetEnvironmentVariable("VARLA_KOL_INSTANCE_ID", "Process")
$previousRuntime = [Environment]::GetEnvironmentVariable("VARLA_KOL_PYTHON", "Process")
[Environment]::SetEnvironmentVariable("VARLA_KOL_INSTANCE_ID", $instanceId, "Process")
[Environment]::SetEnvironmentVariable("VARLA_KOL_PYTHON", $pythonPath, "Process")
try {
    $serverProcess = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList $arguments `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru
}
finally {
    [Environment]::SetEnvironmentVariable("VARLA_KOL_INSTANCE_ID", $previousInstanceId, "Process")
    [Environment]::SetEnvironmentVariable("VARLA_KOL_PYTHON", $previousRuntime, "Process")
}

$deadline = (Get-Date).AddSeconds($WaitSeconds)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    if ($serverProcess.HasExited) {
        break
    }
    $status = Get-CommandCenterStatus
    if ((Test-CommandCenterStatus $status) -and (Test-CommandCenterPage)) {
        $healthy = $true
        break
    }
    Start-Sleep -Milliseconds 500
}

if (-not $healthy) {
    if (-not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id
    }
    throw "The local server did not pass its build and instance safety check. See $stderrLog"
}

$pidPath = Join-Path $runtimeRoot "server.pid"
$metadataPath = Join-Path $runtimeRoot "server.json"
Set-Content -LiteralPath $pidPath -Value ([string]$serverProcess.Id) -Encoding ASCII
[ordered]@{
    pid = $serverProcess.Id
    build_id = $buildId
    instance_id = $instanceId
    bind_host = "127.0.0.1"
    bind_port = 8791
    manual_mode = $true
    auto_mode = $false
    started_at = (Get-Date).ToString("o")
    stdout_log = $stdoutLog
    stderr_log = $stderrLog
} | ConvertTo-Json | Set-Content -LiteralPath $metadataPath -Encoding UTF8

if (-not $NoBrowser) {
    Start-Process $webUrl | Out-Null
}

Write-Output "START_OK"
Write-Output "reused=false"
Write-Output "pid=$($serverProcess.Id)"
Write-Output "build_id=$buildId"
Write-Output "instance_id=$instanceId"
Write-Output "url=$webUrl"
Write-Output "status=local/manual/auto=false"
Write-Output "stdout_log=$stdoutLog"
Write-Output "stderr_log=$stderrLog"
