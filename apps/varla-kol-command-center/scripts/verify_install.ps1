[CmdletBinding()]
param(
    [string]$SourceSkillPath = "",
    [string]$InstalledSkillPath = "",
    [switch]$SkipStart,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($SourceSkillPath)) {
    $SourceSkillPath = Join-Path $projectRoot "skill"
}
if ([string]::IsNullOrWhiteSpace($InstalledSkillPath)) {
    $InstalledSkillPath = Join-Path $env:USERPROFILE ".codex\skills\varla-kol-command-center"
}

$SourceSkillPath = [System.IO.Path]::GetFullPath($SourceSkillPath)
$InstalledSkillPath = [System.IO.Path]::GetFullPath($InstalledSkillPath)
$relativeFiles = @("SKILL.md", "agents\openai.yaml")

foreach ($relativePath in $relativeFiles) {
    $sourceFile = Join-Path $SourceSkillPath $relativePath
    $installedFile = Join-Path $InstalledSkillPath $relativePath
    if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf)) {
        throw "Source Skill file is missing: $relativePath"
    }
    if (-not (Test-Path -LiteralPath $installedFile -PathType Leaf)) {
        throw "Installed Skill file is missing: $relativePath"
    }
    $sourceHash = (Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash
    $installedHash = (Get-FileHash -LiteralPath $installedFile -Algorithm SHA256).Hash
    if ($sourceHash -ne $installedHash) {
        throw "Installed Skill hash mismatch: $relativePath"
    }
}

function Test-MasterSkillStructure {
    param([string]$SkillPath)
    $skillFile = Join-Path $SkillPath "SKILL.md"
    $agentsFile = Join-Path $SkillPath "agents\openai.yaml"
    $skillText = Get-Content -LiteralPath $skillFile -Raw -Encoding UTF8
    $frontmatterPattern = "(?s)\A---\r?\nname: varla-kol-command-center\r?\ndescription: [^\r\n]{40,}\r?\n---\r?\n"
    if ($skillText -notmatch $frontmatterPattern) {
        throw "Installed SKILL.md frontmatter is invalid."
    }
    if (($skillText -split "\r?\n").Count -ge 500) {
        throw "Installed SKILL.md exceeds the 500-line limit."
    }
    $agentsText = Get-Content -LiteralPath $agentsFile -Raw -Encoding UTF8
    $agentsPattern = '(?s)\Ainterface:\r?\n  display_name: "[^"\r\n]+"\r?\n  short_description: "[^"\r\n]{25,64}"\r?\n  default_prompt: "[^"\r\n]*\$varla-kol-command-center[^"\r\n]*"\r?\n?\z'
    if ($agentsText -notmatch $agentsPattern) {
        throw "Installed agents/openai.yaml is invalid."
    }
}
Test-MasterSkillStructure $InstalledSkillPath

if (-not $SkipStart) {
    $startScript = Join-Path $PSScriptRoot "start_server.ps1"
    if ($NoBrowser) {
        & $startScript -NoBrowser
    }
    else {
        & $startScript
    }
    if (-not $?) {
        throw "Local server verification failed."
    }
}

$skillHash = (Get-FileHash -LiteralPath (Join-Path $InstalledSkillPath "SKILL.md") -Algorithm SHA256).Hash
$agentsHash = (Get-FileHash -LiteralPath (Join-Path $InstalledSkillPath "agents\openai.yaml") -Algorithm SHA256).Hash
Write-Output "VERIFY_OK"
Write-Output "installed_path=$InstalledSkillPath"
Write-Output "skill_sha256=$skillHash"
Write-Output "agents_sha256=$agentsHash"
