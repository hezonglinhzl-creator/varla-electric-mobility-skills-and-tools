function Find-CodexExe {
    $root = Join-Path $env:LOCALAPPDATA "OpenAI\Codex\bin"
    $candidate = Get-ChildItem -LiteralPath $root -Recurse -Filter "codex.exe" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($candidate) {
        return $candidate.FullName
    }

    $command = Get-Command codex -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notmatch "WindowsApps") {
        return $command.Source
    }
    return $null
}

function Get-PnpmCommand {
    $fallback = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd"
    if (Test-Path $fallback) {
        return $fallback
    }
    $command = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    return $null
}

function Set-BridgePath {
    param([string]$CodexExe)
    $pnpmRoot = Join-Path $env:LOCALAPPDATA "pnpm"
    $pnpmBin = Join-Path $pnpmRoot "bin"
    $nodeDir = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
    $codexDir = Split-Path -Parent $CodexExe
    $env:PNPM_HOME = $pnpmRoot
    $env:PATH = "$codexDir;$pnpmBin;$pnpmRoot;$nodeDir;" + $env:PATH
}
