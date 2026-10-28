param([switch]$NoBrowser, [switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
$nodeMajor = 0
if ($node) {
    $versionText = (& $node.Source --version 2>$null | Select-Object -First 1)
    if ($versionText -match '^v(\d+)\.') { $nodeMajor = [int]$matches[1] }
}
$dependencies = Test-Path -LiteralPath (Join-Path $ProjectRoot 'node_modules\next\package.json') -PathType Leaf
$ready = [bool]($node -and $npm -and $nodeMajor -ge 22 -and $dependencies)
$checks = [ordered]@{
    node_available = [bool]$node
    node_supported = ($nodeMajor -ge 22)
    npm_available = [bool]$npm
    dependencies_installed = [bool]$dependencies
    starts_worker_automatically = $false
    mode = 'static-dashboard-prototype'
    ready_to_launch_dashboard = $ready
}
if ($CheckOnly) {
    $checks | ConvertTo-Json -Compress
    if (-not $ready) { exit 1 }
    exit 0
}
if (-not $node -or -not $npm -or $nodeMajor -lt 22) { throw 'Install Node.js 22+ with npm, then reopen the terminal.' }
if (-not $dependencies) { throw 'Dependencies are missing. Open this program folder in PowerShell and run npm install first.' }
if (Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction SilentlyContinue) { throw 'Port 3000 is already in use. Close your own conflicting application before starting this dashboard.' }
Write-Host 'Static prototype: no real publishing, no automatic worker. Health endpoint remains a 503 placeholder.'
Write-Host 'Dashboard URL: http://127.0.0.1:3000 (refresh after Next.js finishes starting).'
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:3000' | Out-Null }
Push-Location $ProjectRoot
try {
    $env:MOCK_PUBLISHING = 'true'
    & $npm.Source run dev
    if ($LASTEXITCODE -ne 0) { throw "Dashboard exited with code $LASTEXITCODE" }
} finally { Pop-Location }
