[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$DesktopPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$startScript = Join-Path $ProjectRoot "scripts\start_server.ps1"
$batchLauncher = Join-Path $ProjectRoot "START_KOL_COMMAND_CENTER.bat"

foreach ($requiredFile in @($startScript, $batchLauncher)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required launcher file is unavailable: $(Split-Path -Leaf $requiredFile)"
    }
}
if ($startScript.Contains('"')) {
    throw "The project path cannot contain a double quote."
}

if ([string]::IsNullOrWhiteSpace($DesktopPath)) {
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
}
$DesktopPath = [System.IO.Path]::GetFullPath($DesktopPath)
if (-not (Test-Path -LiteralPath $DesktopPath -PathType Container)) {
    throw "The selected Desktop folder is unavailable."
}

$powerShellPath = (Get-Command powershell.exe -CommandType Application).Source
$shortcutName = "Varla KOL " + [char]0x603B + [char]0x63A7 + [char]0x53F0 + ".lnk"
$shortcutPath = Join-Path $DesktopPath $shortcutName
$arguments = '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $startScript
$iconPath = Join-Path $env:SystemRoot "System32\shell32.dll"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $null
try {
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $powerShellPath
    $shortcut.Arguments = $arguments
    $shortcut.WorkingDirectory = $ProjectRoot
    $shortcut.WindowStyle = 7
    $shortcut.Description = "Start the local manual Varla KOL Command Center"
    $shortcut.IconLocation = "$iconPath,25"
    $shortcut.Save()
}
finally {
    if ($null -ne $shortcut) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
    }
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
}

$verificationShell = New-Object -ComObject WScript.Shell
$installed = $null
try {
    $installed = $verificationShell.CreateShortcut($shortcutPath)
    $valid = (
        (Test-Path -LiteralPath $shortcutPath -PathType Leaf) -and
        $installed.TargetPath -eq $powerShellPath -and
        $installed.Arguments -eq $arguments -and
        $installed.WorkingDirectory -eq $ProjectRoot -and
        [int]$installed.WindowStyle -eq 7
    )
    if (-not $valid) {
        throw "Desktop shortcut verification failed."
    }
}
finally {
    if ($null -ne $installed) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($installed)
    }
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($verificationShell)
}

Write-Output "SHORTCUT_OK"
Write-Output "shortcut_path=$shortcutPath"
Write-Output "url=http://127.0.0.1:8791/"
