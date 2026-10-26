param(
    [string]$InstallRoot = (Join-Path $env:USERPROFILE ".codex\skills")
)

$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillName = "viral-product-video-replicator"
$SkillSource = Join-Path $PackageRoot $SkillName
$SkillDest = Join-Path $InstallRoot $SkillName

Write-Host ""
Write-Host "Package root: $PackageRoot"
Write-Host "Install root: $InstallRoot"

if (-not (Test-Path -LiteralPath (Join-Path $SkillSource "SKILL.md"))) {
    throw "Cannot find skill source. Expected: $SkillSource\SKILL.md"
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

if (Test-Path -LiteralPath $SkillDest) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $BackupDest = "$SkillDest.backup-$stamp"
    Write-Host "Existing skill found. Backing it up to:"
    Write-Host $BackupDest
    Move-Item -LiteralPath $SkillDest -Destination $BackupDest
}

Copy-Item -LiteralPath $SkillSource -Destination $SkillDest -Recurse

if (-not (Test-Path -LiteralPath (Join-Path $SkillDest "SKILL.md"))) {
    throw "Install failed. SKILL.md was not copied to $SkillDest"
}

Write-Host ""
Write-Host "Installed successfully:"
Write-Host $SkillDest
Write-Host ""
Write-Host "Next step: restart Codex, then ask it to use viral-product-video-replicator."
