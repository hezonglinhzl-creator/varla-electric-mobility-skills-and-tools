$ErrorActionPreference = "SilentlyContinue"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$reservedPorts = @(8766)
$port = $null

foreach ($candidate in 8765, 8767, 8768, 8769, 8770, 8771, 8772, 8773, 8774, 8775) {
  if ($reservedPorts -contains $candidate) { continue }
  $inUse = Get-NetTCPConnection -LocalPort $candidate -State Listen
  if (-not $inUse) {
    $port = $candidate
    break
  }
}

if (-not $port) {
  Write-Host "No free local port found in the safe range. Please close one local preview window and try again."
  exit 1
}

$url = "http://127.0.0.1:$port/index.html"

$pythonCandidates = @(
  (Get-Command "python" -ErrorAction SilentlyContinue).Source,
  (Get-Command "py" -ErrorAction SilentlyContinue).Source,
  "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
) | Where-Object { $_ -and (Test-Path $_) -and ($_ -notlike "*\WindowsApps\python.exe") }

$pythonExe = $pythonCandidates | Select-Object -First 1
if (-not $pythonExe) {
  Write-Host "No usable Python executable found. Please install Python or run from Codex with bundled Python available."
  exit 1
}

Start-Process -FilePath $pythonExe -ArgumentList "-m", "http.server", "$port", "--bind", "127.0.0.1" -WorkingDirectory $root -WindowStyle Hidden
Start-Sleep -Seconds 1

$chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
$chrome2 = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$edge2 = "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe"

if (Test-Path $chrome) {
  Start-Process -FilePath $chrome -ArgumentList "--app=$url", "--window-size=560,820"
} elseif (Test-Path $chrome2) {
  Start-Process -FilePath $chrome2 -ArgumentList "--app=$url", "--window-size=560,820"
} elseif (Test-Path $edge) {
  Start-Process -FilePath $edge -ArgumentList "--app=$url", "--window-size=560,820"
} elseif (Test-Path $edge2) {
  Start-Process -FilePath $edge2 -ArgumentList "--app=$url", "--window-size=560,820"
} else {
  Start-Process $url
}
