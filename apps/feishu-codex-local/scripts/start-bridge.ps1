$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$running = Get-Process -Name "cc-connect" -ErrorAction SilentlyContinue
if ($running) {
    Write-Output "CC_CONNECT_ALREADY_RUNNING PID=$($running.Id -join ',')"
    exit 0
}

$codexExe = Find-CodexExe
if (-not $codexExe) {
    throw "A working Codex CLI was not found."
}
Set-BridgePath -CodexExe $codexExe

$config = Join-Path $env:USERPROFILE ".cc-connect\config.toml"
if (-not (Test-Path $config)) {
    throw "Bridge config is missing. Run configure-bridge.ps1 first."
}

$cc = Join-Path (Join-Path $env:LOCALAPPDATA "pnpm") "bin\cc-connect.cmd"
if (-not (Test-Path $cc)) {
    $command = Get-Command cc-connect -ErrorAction SilentlyContinue
    if ($command) {
        $cc = $command.Source
    }
}
if (-not (Test-Path $cc)) {
    throw "cc-connect is not installed."
}

& $cc --config $config
