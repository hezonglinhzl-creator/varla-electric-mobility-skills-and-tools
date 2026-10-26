[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetPath,
    [string]$BackupRoot = (Join-Path $env:LOCALAPPDATA "VarlaKOLCommandCenter\skill-backups"),
    [string]$SourcePath = "",
    [ValidateSet("", "apply", "verify")]
    [string]$InjectFailure = "",
    [string]$PythonPath = "",
    [ValidateRange(0, 10000)]
    [int]$PauseAfterSnapshotMilliseconds = 0,
    [ValidateRange(0, 10000)]
    [int]$HoldLockMilliseconds = 0
)

$ErrorActionPreference = "Stop"
$reviewedRelativePaths = @(
    "SKILL.md",
    "agents\openai.yaml",
    "references\safety-and-routing.md",
    "references\setup-windows.md",
    "scripts\gmail_automation.py",
    "scripts\attachment_utils.py",
    "scripts\requirements.txt"
)
function Get-NormalizedFullPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    $root = [IO.Path]::GetPathRoot($full)
    if ($full.Length -gt $root.Length) {
        return $full.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    }
    return $full
}

$defaultSource = Join-Path $PSScriptRoot "..\skill_sources\varla-gmail-automation"
$sourceRoot = Get-NormalizedFullPath $(if ($SourcePath) { $SourcePath } else { $defaultSource })
$targetRoot = Get-NormalizedFullPath $TargetPath
$backupRootFull = Get-NormalizedFullPath $BackupRoot
$targetParentInfo = [IO.Directory]::GetParent($targetRoot)
if ($null -eq $targetParentInfo) { throw "Target path must have a parent directory." }
$targetParent = $targetParentInfo.FullName
$transactionId = (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + [guid]::NewGuid().ToString("N")
$stagingRoot = Join-Path $targetParent (".gmail-install-staging-" + $transactionId)
$backupPath = Join-Path $backupRootFull $transactionId
$createdFiles = New-Object System.Collections.Generic.List[string]
$createdDirectories = New-Object System.Collections.Generic.List[string]
$existingFiles = New-Object System.Collections.Generic.List[object]
$frozenFiles = New-Object System.Collections.Generic.List[object]
$lockStream = $null
$stage = "preflight"
$verifyGmailPyc = ""
$verifyAttachmentPyc = ""

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-TextSha256([string]$Value) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Assert-NoReparseExistingComponents([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    $root = [IO.Path]::GetPathRoot($full)
    $current = $root
    $remainder = $full.Substring($root.Length)
    foreach ($part in $remainder.Split(@("\", "/"), [StringSplitOptions]::RemoveEmptyEntries)) {
        $current = Join-Path $current $part
        if ([IO.File]::Exists($current) -or [IO.Directory]::Exists($current)) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "REPARSE_POINT rejected."
            }
        }
    }
}

function New-KnownDirectory([string]$Path) {
    Assert-NoReparseExistingComponents $Path
    if (-not [IO.Directory]::Exists($Path)) {
        [IO.Directory]::CreateDirectory($Path) | Out-Null
        $script:createdDirectories.Add($Path)
    }
    Assert-NoReparseExistingComponents $Path
}

function Remove-KnownFile([string]$Path) {
    if ([IO.File]::Exists($Path)) {
        [IO.File]::Delete($Path)
    }
}

function Remove-KnownEmptyDirectory([string]$Path) {
    if ([IO.Directory]::Exists($Path) -and
        [IO.Directory]::GetFileSystemEntries($Path).Count -eq 0) {
        [IO.Directory]::Delete($Path, $false)
    }
}

function Assert-FrozenHash([string]$Path, [string]$FrozenHash) {
    if (-not [IO.File]::Exists($Path) -or (Get-Sha256 $Path) -ne $FrozenHash) {
        throw "Frozen file hash verification failed."
    }
}

function Resolve-Python {
    if ($PythonPath) { return [IO.Path]::GetFullPath($PythonPath) }
    foreach ($candidate in @("python.exe", "py.exe")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    throw "Python runtime not found."
}

function Invoke-PythonCheck([string]$Python, [string[]]$Arguments) {
    & $Python @Arguments *> $null
    if ($LASTEXITCODE -ne 0) { throw "Installed Gmail skill verification failed." }
}

function Remove-TransactionArtifacts {
    foreach ($file in $frozenFiles) {
        Remove-KnownFile (Join-Path $stagingRoot $file.Relative)
    }
    if ($verifyGmailPyc) { Remove-KnownFile $verifyGmailPyc }
    if ($verifyAttachmentPyc) { Remove-KnownFile $verifyAttachmentPyc }
    $stagingDirectories = $createdDirectories |
        Where-Object {
            $_ -eq $stagingRoot -or
            $_.StartsWith($stagingRoot + [IO.Path]::DirectorySeparatorChar)
        } |
        Sort-Object Length -Descending
    foreach ($directory in $stagingDirectories) {
        Remove-KnownEmptyDirectory $directory
    }
}

try {
    Assert-NoReparseExistingComponents $sourceRoot
    Assert-NoReparseExistingComponents $targetRoot
    Assert-NoReparseExistingComponents $backupRootFull
    if (-not [IO.Directory]::Exists($sourceRoot)) {
        throw "Canonical Gmail skill source is missing."
    }
    foreach ($relative in $reviewedRelativePaths) {
        $source = Join-Path $sourceRoot $relative
        Assert-NoReparseExistingComponents $source
        if (-not [IO.File]::Exists($source)) {
            throw "Reviewed Gmail skill file is missing."
        }
        $frozenFiles.Add([pscustomobject]@{
            Source = $source
            Relative = $relative
            Hash = Get-Sha256 $source
        })
        Assert-NoReparseExistingComponents (Join-Path $targetRoot $relative)
        Assert-NoReparseExistingComponents (Join-Path $backupPath $relative)
        Assert-NoReparseExistingComponents (Join-Path $stagingRoot $relative)
    }

    if ($PauseAfterSnapshotMilliseconds -gt 0) {
        Write-Output "SNAPSHOT_READY"
        Start-Sleep -Milliseconds $PauseAfterSnapshotMilliseconds
    }

    if (-not [IO.Directory]::Exists($targetParent)) {
        [IO.Directory]::CreateDirectory($targetParent) | Out-Null
    }
    Assert-NoReparseExistingComponents $targetParent
    $lockName = ".gmail-skill-update-" + (Get-TextSha256 $targetRoot.ToLowerInvariant()) + ".lock"
    $lockPath = Join-Path $targetParent $lockName
    Assert-NoReparseExistingComponents $lockPath
    try {
        $lockStream = [IO.File]::Open(
            $lockPath,
            [IO.FileMode]::OpenOrCreate,
            [IO.FileAccess]::ReadWrite,
            [IO.FileShare]::None
        )
    }
    catch {
        Write-Output "LOCKED"
        Write-Error "Another Gmail skill update is already running for this target."
        exit 1
    }
    if ($HoldLockMilliseconds -gt 0) {
        Start-Sleep -Milliseconds $HoldLockMilliseconds
    }

    $stage = "stage-copy"
    New-KnownDirectory $stagingRoot
    foreach ($file in $frozenFiles) {
        Assert-FrozenHash $file.Source $file.Hash
        $staged = Join-Path $stagingRoot $file.Relative
        New-KnownDirectory ([IO.Directory]::GetParent($staged).FullName)
        [IO.File]::Copy($file.Source, $staged, $false)
        Assert-FrozenHash $staged $file.Hash
    }

    $stage = "backup"
    foreach ($file in $frozenFiles) {
        $destination = Join-Path $targetRoot $file.Relative
        if ([IO.File]::Exists($destination)) {
            $originalHash = Get-Sha256 $destination
            $backupFile = Join-Path $backupPath $file.Relative
            Assert-NoReparseExistingComponents $backupFile
            [IO.Directory]::CreateDirectory([IO.Directory]::GetParent($backupFile).FullName) | Out-Null
            Assert-NoReparseExistingComponents ([IO.Directory]::GetParent($backupFile).FullName)
            [IO.File]::Copy($destination, $backupFile, $false)
            Assert-FrozenHash $backupFile $originalHash
            $existingFiles.Add([pscustomobject]@{
                Relative = $file.Relative
                Hash = $originalHash
            })
        }
    }

    $stage = "apply"
    New-KnownDirectory $targetRoot
    $applyCount = 0
    foreach ($file in $frozenFiles) {
        $destination = Join-Path $targetRoot $file.Relative
        New-KnownDirectory ([IO.Directory]::GetParent($destination).FullName)
        if (-not [IO.File]::Exists($destination)) { $createdFiles.Add($destination) }
        [IO.File]::Copy((Join-Path $stagingRoot $file.Relative), $destination, $true)
        Assert-FrozenHash $destination $file.Hash
        $applyCount += 1
        if ($InjectFailure -eq "apply" -and $applyCount -eq 1) {
            throw "Injected apply failure."
        }
    }

    $stage = "python-compile"
    $python = Resolve-Python
    $verifyGmailPyc = Join-Path $stagingRoot "verify-gmail.pyc"
    $verifyAttachmentPyc = Join-Path $stagingRoot "verify-attachment.pyc"
    $compileCode = "import py_compile,sys; py_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)"
    Invoke-PythonCheck $python @("-c", $compileCode,
        (Join-Path $targetRoot "scripts\gmail_automation.py"), $verifyGmailPyc)
    Invoke-PythonCheck $python @("-c", $compileCode,
        (Join-Path $targetRoot "scripts\attachment_utils.py"), $verifyAttachmentPyc)
    $stage = "cli-help"
    Invoke-PythonCheck $python @("-B", (Join-Path $targetRoot "scripts\gmail_automation.py"), "--help")
    if ($InjectFailure -eq "verify") { throw "Injected verification failure." }

    foreach ($file in $frozenFiles) {
        Assert-FrozenHash (Join-Path $targetRoot $file.Relative) $file.Hash
    }
    Remove-TransactionArtifacts
    Write-Output "INSTALL_OK"
    Write-Output ("backup_path=" + $backupPath)
    foreach ($file in $frozenFiles) {
        Write-Output ("sha256[" + $file.Relative.Replace("\", "/") + "]=" + $file.Hash)
    }
    exit 0
}
catch {
    $failureMessage = $_.Exception.Message
    $rollbackOk = $true
    foreach ($record in $existingFiles) {
        try {
            $backupFile = Join-Path $backupPath $record.Relative
            $destination = Join-Path $targetRoot $record.Relative
            Assert-FrozenHash $backupFile $record.Hash
            [IO.Directory]::CreateDirectory([IO.Directory]::GetParent($destination).FullName) | Out-Null
            [IO.File]::Copy($backupFile, $destination, $true)
            Assert-FrozenHash $destination $record.Hash
        }
        catch { $rollbackOk = $false }
    }
    foreach ($file in $createdFiles) {
        try {
            Remove-KnownFile $file
            if ([IO.File]::Exists($file)) { $rollbackOk = $false }
        }
        catch { $rollbackOk = $false }
    }
    try { Remove-TransactionArtifacts } catch { $rollbackOk = $false }
    $targetDirectories = $createdDirectories |
        Where-Object {
            $_ -eq $targetRoot -or
            $_.StartsWith($targetRoot + [IO.Path]::DirectorySeparatorChar)
        } |
        Sort-Object Length -Descending
    foreach ($directory in $targetDirectories) {
        try { Remove-KnownEmptyDirectory $directory } catch { $rollbackOk = $false }
    }
    foreach ($record in $existingFiles) {
        try {
            Assert-FrozenHash (Join-Path $targetRoot $record.Relative) $record.Hash
        }
        catch { $rollbackOk = $false }
    }
    foreach ($file in $createdFiles) {
        if ([IO.File]::Exists($file)) { $rollbackOk = $false }
    }
    if ($failureMessage -like "REPARSE_POINT*") { Write-Output "REPARSE_POINT" }
    if ($rollbackOk) { Write-Output "ROLLBACK_OK" } else { Write-Output "ROLLBACK_FAILED" }
    Write-Output ("failure_stage=" + $stage)
    Write-Error "Gmail skill installation failed."
    exit 1
}
finally {
    if ($null -ne $lockStream) {
        $lockStream.Dispose()
    }
}
