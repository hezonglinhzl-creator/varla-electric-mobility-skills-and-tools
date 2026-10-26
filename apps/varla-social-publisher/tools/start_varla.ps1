param([switch]$NoBrowser)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$NodeDir = Join-Path $ProjectRoot "tools\node-v22.23.1-win-x64"
$Npm = Join-Path $NodeDir "npm.cmd"
$RedisDir = Join-Path $ProjectRoot "tools\redis-8.8.0\Redis-8.8.0-Windows-x64-msys2"
$RedisServer = Join-Path $RedisDir "redis-server.exe"
$RedisCli = Join-Path $RedisDir "redis-cli.exe"
$RuntimeDir = Join-Path $ProjectRoot "runtime"
$LogDir = Join-Path $RuntimeDir "logs"
$RedisData = Join-Path $RuntimeDir "redis-data"

New-Item -ItemType Directory -Force -Path $LogDir, $RedisData | Out-Null
$env:PATH = "$NodeDir;$env:PATH"

function Test-Port([int]$Port) {
  return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

if (-not (Test-Path -LiteralPath $Npm)) { throw "Portable Node.js is missing: $Npm" }
if (-not (Test-Path -LiteralPath $RedisServer)) { throw "Portable Redis is missing: $RedisServer" }

if (-not (Test-Port 6379)) {
  $redisOut = Join-Path $LogDir "redis.stdout.log"
  $redisErr = Join-Path $LogDir "redis.stderr.log"
  $redis = Start-Process -FilePath $RedisServer -ArgumentList @("--port", "6379", "--dir", $RedisData, "--appendonly", "yes") -WorkingDirectory $RedisDir -WindowStyle Hidden -RedirectStandardOutput $redisOut -RedirectStandardError $redisErr -PassThru
  Set-Content -LiteralPath (Join-Path $RuntimeDir "redis.pid") -Value $redis.Id
  for ($i = 0; $i -lt 30; $i++) {
    if ((& $RedisCli -p 6379 ping 2>$null) -eq "PONG") { break }
    Start-Sleep -Milliseconds 300
  }
}

if ((& $RedisCli -p 6379 ping 2>$null) -ne "PONG") { throw "Redis did not become ready. See runtime\logs\redis.stderr.log" }

if (-not (Test-Port 3000)) {
  $webOut = Join-Path $LogDir "web.stdout.log"
  $webErr = Join-Path $LogDir "web.stderr.log"
  $web = Start-Process -FilePath $Npm -ArgumentList @("run", "dev") -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $webOut -RedirectStandardError $webErr -PassThru
  Set-Content -LiteralPath (Join-Path $RuntimeDir "web.pid") -Value $web.Id
}

$workerOut = Join-Path $LogDir "worker.stdout.log"
$workerErr = Join-Path $LogDir "worker.stderr.log"
$workerAlreadyRunning = Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*$ProjectRoot*apps*worker*" -or $_.CommandLine -like "*tsx*src/index.ts*" }
if (-not $workerAlreadyRunning) {
  $env:RUN_WORKER = "true"
  $env:REDIS_URL = "redis://127.0.0.1:6379"
  $env:MOCK_PUBLISHING = "true"
  $worker = Start-Process -FilePath $Npm -ArgumentList @("run", "worker") -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $workerOut -RedirectStandardError $workerErr -PassThru
  Set-Content -LiteralPath (Join-Path $RuntimeDir "worker.pid") -Value $worker.Id
}

$ready = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:3000" -TimeoutSec 2
    if ($response.StatusCode -eq 200) { $ready = $true; break }
  } catch {}
  Start-Sleep -Milliseconds 500
}

if (-not $ready) { throw "Web app did not become ready. See runtime\logs\web.stderr.log" }
Write-Host "Varla Social Publisher is running at http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "Redis: PONG | Worker: started | Mock publishing: enabled"
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:3000" }
