$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$codexExe = Find-CodexExe
$config = Join-Path $env:USERPROFILE ".cc-connect\config.toml"
$bridge = Get-Process -Name "cc-connect" -ErrorAction SilentlyContinue

Write-Output "=== CC-Connect Local Status ==="
Write-Output ("Config: " + $(if (Test-Path $config) { "OK" } else { "MISSING" }))
Write-Output ("Bridge: " + $(if ($bridge) { "RUNNING (PID $($bridge.Id -join ','))" } else { "STOPPED" }))

if ($codexExe) {
    Set-BridgePath -CodexExe $codexExe
    Write-Output "Codex path: $codexExe"
    & $codexExe --version
    & $codexExe login status
} else {
    Write-Output "Codex CLI: NOT FOUND"
}

$cc = Join-Path (Join-Path $env:LOCALAPPDATA "pnpm") "bin\cc-connect.cmd"
if (Test-Path $cc) {
    & $cc --version
} else {
    Write-Output "CC-Connect: NOT FOUND"
}
