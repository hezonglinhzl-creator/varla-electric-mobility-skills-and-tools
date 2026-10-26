param(
  [switch]$SkipDreaminaInstall
)

$ErrorActionPreference = 'Stop'

function Say($Text) {
  Write-Host $Text
}

function Ensure-Directory($Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path | Out-Null
  }
}

function Copy-SkillSubDirectory($Name) {
  $sourceDir = Join-Path $sourceSkillDir $Name
  if (-not (Test-Path -LiteralPath $sourceDir)) {
    return
  }

  $targetDir = Join-Path $targetSkillDir $Name
  Ensure-Directory $targetDir
  Copy-Item -Path (Join-Path $sourceDir '*') -Destination $targetDir -Recurse -Force
  Say "Installed $Name to: $targetDir"
}

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceSkillDir = Join-Path $packageRoot 'image2-motion-agent'
$userProfile = [Environment]::GetFolderPath('UserProfile')
$codexSkillRoot = Join-Path $userProfile '.codex\skills'
$targetSkillDir = Join-Path $codexSkillRoot 'image2-motion-agent'
$installBinDir = Join-Path $userProfile 'bin'
$dreaminaExe = Join-Path $installBinDir 'dreamina.exe'

Say '== Image2 Motion Agent installer =='
Say "Package: $packageRoot"

if (-not (Test-Path -LiteralPath (Join-Path $sourceSkillDir 'SKILL.md'))) {
  throw "Missing SKILL.md in package: $sourceSkillDir"
}

Ensure-Directory $codexSkillRoot
Ensure-Directory $targetSkillDir
Copy-Item -LiteralPath (Join-Path $sourceSkillDir 'SKILL.md') -Destination (Join-Path $targetSkillDir 'SKILL.md') -Force
if (Test-Path -LiteralPath (Join-Path $sourceSkillDir 'README.md')) {
  Copy-Item -LiteralPath (Join-Path $sourceSkillDir 'README.md') -Destination (Join-Path $targetSkillDir 'README.md') -Force
}
Copy-SkillSubDirectory 'scripts'
Copy-SkillSubDirectory 'references'
Say "Installed skill to: $targetSkillDir"

if (-not $SkipDreaminaInstall) {
  Ensure-Directory $installBinDir
  if (Test-Path -LiteralPath $dreaminaExe) {
    Say "Dreamina CLI already exists: $dreaminaExe"
  } else {
    $downloadUrl = 'https://lf3-static.bytednsdoc.com/obj/eden-cn/psj_hupthlyk/ljhwZthlaukjlkulzlp/dreamina_cli_beta/dreamina_cli_windows_amd64.exe'
    Say 'Downloading Dreamina CLI for Windows...'
    Invoke-WebRequest -Uri $downloadUrl -OutFile $dreaminaExe -UseBasicParsing -TimeoutSec 180
    Say "Installed Dreamina CLI to: $dreaminaExe"
  }

  $currentUserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  if ([string]::IsNullOrWhiteSpace($currentUserPath)) {
    [Environment]::SetEnvironmentVariable('Path', $installBinDir, 'User')
    Say "Added to user PATH: $installBinDir"
  } elseif (-not ($currentUserPath.Split(';') -contains $installBinDir)) {
    [Environment]::SetEnvironmentVariable('Path', $currentUserPath + ';' + $installBinDir, 'User')
    Say "Added to user PATH: $installBinDir"
  } else {
    Say "User PATH already contains: $installBinDir"
  }

  $env:Path = $installBinDir + ';' + $env:Path
  & $dreaminaExe --help | Select-Object -First 8
}

Say ''
Say 'Done.'
Say 'Next steps:'
Say '1. Restart Codex so it can load the skill.'
Say '2. In a new PowerShell window, run: dreamina login'
Say '3. Use the skill with an image, review prompts first, then confirm before generating.'
