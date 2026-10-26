$ErrorActionPreference = "Stop"

$configDir = Join-Path $env:USERPROFILE ".cc-connect"
$configPath = Join-Path $configDir "config.toml"
$defaultWorkDir = Join-Path $env:USERPROFILE "Documents\Codex-Feishu"

$appId = Read-Host "Feishu app_id"
$secureSecret = Read-Host "Feishu app_secret" -AsSecureString
$allowFrom = Read-Host "Allowed user open_id"
$workDir = Read-Host "Codex work directory [$defaultWorkDir]"
if ([string]::IsNullOrWhiteSpace($workDir)) {
    $workDir = $defaultWorkDir
}
$model = Read-Host "Codex model [gpt-5.6-sol]"
if ([string]::IsNullOrWhiteSpace($model)) {
    $model = "gpt-5.6-sol"
}

$secretPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret)
try {
    $secret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPtr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPtr)
}

foreach ($pair in @{"app_id"=$appId; "app_secret"=$secret; "open_id"=$allowFrom}) {
    if ([string]::IsNullOrWhiteSpace($pair.Value)) {
        throw "$($pair.Key) is required."
    }
}

New-Item -ItemType Directory -Path $configDir -Force | Out-Null
New-Item -ItemType Directory -Path $workDir -Force | Out-Null
$escapedWorkDir = $workDir.Replace("\", "\\")

$config = @"
language = "zh"

[log]
level = "info"

[[projects]]
name = "my-codex"
admin_from = "$allowFrom"

[projects.agent]
type = "codex"

[projects.agent.options]
work_dir = "$escapedWorkDir"
mode = "yolo"
model = "$model"

[[projects.platforms]]
type = "feishu"

[projects.platforms.options]
app_id = "$appId"
app_secret = "$secret"
enable_feishu_card = false
allow_from = "$allowFrom"
"@

Set-Content -LiteralPath $configPath -Value $config -Encoding UTF8
Write-Output "CONFIG_OK=$configPath"
