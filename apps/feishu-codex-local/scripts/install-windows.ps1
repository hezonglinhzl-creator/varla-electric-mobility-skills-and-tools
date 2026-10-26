$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$codexExe = Find-CodexExe
if (-not $codexExe) {
    throw "A working Codex CLI was not found. Install and log in to Codex first."
}
Set-BridgePath -CodexExe $codexExe

$pnpm = Get-PnpmCommand
$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($pnpm) {
    $pnpmRoot = Join-Path $env:LOCALAPPDATA "pnpm"
    $pnpmBin = Join-Path $pnpmRoot "bin"
    New-Item -ItemType Directory -Path $pnpmBin -Force | Out-Null
    $env:PNPM_HOME = $pnpmRoot
    $env:PATH = "$pnpmBin;$pnpmRoot;" + $env:PATH
    & $pnpm add --global "cc-connect@1.4.1"
} elseif ($npm) {
    & $npm.Source install --global "cc-connect@1.4.1"
} else {
    throw "Neither npm nor the Codex bundled pnpm runtime is available."
}

if ($LASTEXITCODE -ne 0) {
    throw "cc-connect installation failed."
}

$cc = Join-Path (Join-Path $env:LOCALAPPDATA "pnpm") "bin\cc-connect.cmd"
if (-not (Test-Path $cc)) {
    $command = Get-Command cc-connect -ErrorAction SilentlyContinue
    if ($command) {
        $cc = $command.Source
    }
}
if (-not (Test-Path $cc)) {
    throw "cc-connect command was not found after installation."
}

& $codexExe --version
& $codexExe login status
& $cc --version
Write-Output "INSTALL_OK"
