param([switch]$Overwrite)

$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'skills'
$target = Join-Path $env:USERPROFILE '.codex\skills'
if (-not (Test-Path -LiteralPath $source)) { throw "找不到 skills 目录: $source" }
New-Item -ItemType Directory -Path $target -Force | Out-Null

$installed = 0
$skipped = 0
Get-ChildItem -LiteralPath $source -Directory | ForEach-Object {
    $dest = Join-Path $target $_.Name
    if ((Test-Path -LiteralPath $dest) -and -not $Overwrite) {
        $existingSkill = Join-Path $dest 'SKILL.md'
        if (-not (Test-Path -LiteralPath $existingSkill)) {
            Copy-Item -LiteralPath (Join-Path $_.FullName 'SKILL.md') -Destination $existingSkill
            Write-Host "已补齐 SKILL.md: $($_.Name)"
            $installed++
            return
        }
        Write-Host "跳过已有 Skill: $($_.Name)"
        $skipped++
        return
    }
    if (Test-Path -LiteralPath $dest) {
        # Copy-Item merges with an existing directory. This script never deletes files.
        Copy-Item -Path (Join-Path $_.FullName '*') -Destination $dest -Recurse -Force
    } else {
        Copy-Item -LiteralPath $_.FullName -Destination $dest -Recurse
    }
    Write-Host "已安装: $($_.Name)"
    $installed++
}
Write-Host "完成：安装 $installed 个，跳过 $skipped 个。请重新打开 Codex 以刷新 Skill 列表。"
