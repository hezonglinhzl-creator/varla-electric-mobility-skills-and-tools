$ErrorActionPreference = "Stop"

$SkillPath = Join-Path $env:USERPROFILE ".codex\skills\viral-product-video-replicator"
$SkillFile = Join-Path $SkillPath "SKILL.md"

Write-Host ""
Write-Host "Checking:"
Write-Host $SkillFile

if (Test-Path -LiteralPath $SkillFile) {
    Write-Host ""
    Write-Host "OK: skill is installed."
    Write-Host "Restart Codex if it was already open."
} else {
    Write-Host ""
    Write-Host "Not installed yet. Run 安装到Codex.cmd first."
    exit 1
}
