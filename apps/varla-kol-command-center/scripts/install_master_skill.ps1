[CmdletBinding()]
param(
    [string]$TargetPath = "",
    [string]$BackupRoot = "",
    [ValidateSet("none", "second-copy", "verify")]
    [string]$InjectFailure = "none"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Remove-EmptyDirectory {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path -PathType Container) {
        $children = @(Get-ChildItem -LiteralPath $Path -Force)
        if ($children.Count -eq 0) {
            Remove-Item -LiteralPath $Path
        }
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceSkill = Join-Path $projectRoot "skill"
if ([string]::IsNullOrWhiteSpace($TargetPath)) {
    $TargetPath = Join-Path $env:USERPROFILE ".codex\skills\varla-kol-command-center"
}
if ([string]::IsNullOrWhiteSpace($BackupRoot)) {
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw "LOCALAPPDATA is unavailable."
    }
    $BackupRoot = Join-Path $env:LOCALAPPDATA "VarlaKOLCommandCenter\backups"
}

$TargetPath = [System.IO.Path]::GetFullPath($TargetPath)
$BackupRoot = [System.IO.Path]::GetFullPath($BackupRoot)
$sourceSkillFile = Join-Path $sourceSkill "SKILL.md"
$sourceAgentsFile = Join-Path $sourceSkill "agents\openai.yaml"
if (-not (Test-Path -LiteralPath $sourceSkillFile -PathType Leaf)) {
    throw "Master Skill source is missing SKILL.md."
}
if (-not (Test-Path -LiteralPath $sourceAgentsFile -PathType Leaf)) {
    throw "Master Skill source is missing agents/openai.yaml."
}

# Validate the complete source before creating staging, backup, or target files.
$sourceSkillText = Get-Content -LiteralPath $sourceSkillFile -Raw -Encoding UTF8
$sourceFrontmatterPattern = "(?s)\A---\r?\nname: varla-kol-command-center\r?\ndescription: [^\r\n]{40,}\r?\n---\r?\n"
if ($sourceSkillText -notmatch $sourceFrontmatterPattern) {
    throw "Master Skill source frontmatter is invalid."
}
if (($sourceSkillText -split "\r?\n").Count -ge 500) {
    throw "Master Skill source exceeds the 500-line limit."
}
$sourceAgentsText = Get-Content -LiteralPath $sourceAgentsFile -Raw -Encoding UTF8
$sourceAgentsPattern = '(?s)\Ainterface:\r?\n  display_name: "[^"\r\n]+"\r?\n  short_description: "[^"\r\n]{25,64}"\r?\n  default_prompt: "[^"\r\n]*\$varla-kol-command-center[^"\r\n]*"\r?\n?\z'
if ($sourceAgentsText -notmatch $sourceAgentsPattern) {
    throw "Master Skill source agents/openai.yaml is invalid."
}

$relativeFiles = @("SKILL.md", "agents\openai.yaml")
$sourceFiles = @{
    "SKILL.md" = $sourceSkillFile
    "agents\openai.yaml" = $sourceAgentsFile
}
$targetExisted = Test-Path -LiteralPath $TargetPath -PathType Container
$targetAgents = Join-Path $TargetPath "agents"
$targetAgentsExisted = Test-Path -LiteralPath $targetAgents -PathType Container
$originals = @{}
foreach ($relativePath in $relativeFiles) {
    $originalPath = Join-Path $TargetPath $relativePath
    $originalExists = Test-Path -LiteralPath $originalPath -PathType Leaf
    $originals[$relativePath] = @{
        exists = $originalExists
        sha256 = $(if ($originalExists) { Get-Sha256 $originalPath } else { $null })
    }
}

New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
$transactionId = "$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$stagingPath = Join-Path $BackupRoot ".staging-varla-kol-command-center-$transactionId"
$stagingAgents = Join-Path $stagingPath "agents"
$stagingSkillFile = Join-Path $stagingPath "SKILL.md"
$stagingAgentsFile = Join-Path $stagingAgents "openai.yaml"
$backupPath = $null
$applyStarted = $false

try {
    New-Item -ItemType Directory -Path $stagingAgents | Out-Null
    Copy-Item -LiteralPath $sourceSkillFile -Destination $stagingSkillFile
    Copy-Item -LiteralPath $sourceAgentsFile -Destination $stagingAgentsFile
    foreach ($relativePath in $relativeFiles) {
        $stagedFile = Join-Path $stagingPath $relativePath
        if ((Get-Sha256 $stagedFile) -ne (Get-Sha256 $sourceFiles[$relativePath])) {
            throw "Staging hash mismatch: $relativePath"
        }
    }

    if ($targetExisted) {
        $backupPath = Join-Path $BackupRoot "varla-kol-command-center-$transactionId"
        if (Test-Path -LiteralPath $backupPath) {
            throw "Backup destination already exists; refusing to overwrite it."
        }
        New-Item -ItemType Directory -Path $backupPath | Out-Null
        $targetPrefix = $TargetPath.TrimEnd("\", "/")
        $existingFiles = @(Get-ChildItem -LiteralPath $TargetPath -Recurse -File)
        foreach ($existingFile in $existingFiles) {
            $relativePath = $existingFile.FullName.Substring($targetPrefix.Length).TrimStart("\", "/")
            $backupFile = Join-Path $backupPath $relativePath
            $backupParent = Split-Path -Parent $backupFile
            if (-not (Test-Path -LiteralPath $backupParent -PathType Container)) {
                New-Item -ItemType Directory -Path $backupParent -Force | Out-Null
            }
            if (Test-Path -LiteralPath $backupFile) {
                throw "Backup file already exists; refusing to overwrite it: $relativePath"
            }
            Copy-Item -LiteralPath $existingFile.FullName -Destination $backupFile
            if ((Get-Sha256 $backupFile) -ne (Get-Sha256 $existingFile.FullName)) {
                throw "Backup hash mismatch: $relativePath"
            }
        }
    }

    try {
        New-Item -ItemType Directory -Path $targetAgents -Force | Out-Null
        $applyStarted = $true
        Copy-Item -LiteralPath $stagingSkillFile -Destination (Join-Path $TargetPath "SKILL.md") -Force
        if ($InjectFailure -eq "second-copy") {
            throw "Injected failure before the second target copy."
        }
        Copy-Item -LiteralPath $stagingAgentsFile -Destination (Join-Path $targetAgents "openai.yaml") -Force
        if ($InjectFailure -eq "verify") {
            throw "Injected failure before installed verification."
        }

        $verifyScript = Join-Path $PSScriptRoot "verify_install.ps1"
        & $verifyScript -SourceSkillPath $sourceSkill -InstalledSkillPath $TargetPath -SkipStart
        if (-not $?) {
            throw "Installed Skill verification failed."
        }
    }
    catch {
        $installError = $_.Exception.Message
        if ($applyStarted) {
            foreach ($relativePath in $relativeFiles) {
                $targetFile = Join-Path $TargetPath $relativePath
                $original = $originals[$relativePath]
                if ($original.exists) {
                    if ($null -eq $backupPath) {
                        throw "Rollback backup is unavailable for $relativePath"
                    }
                    $backupFile = Join-Path $backupPath $relativePath
                    Copy-Item -LiteralPath $backupFile -Destination $targetFile -Force
                    if ((Get-Sha256 $targetFile) -ne $original.sha256) {
                        throw "Rollback hash mismatch: $relativePath"
                    }
                }
                elseif (Test-Path -LiteralPath $targetFile -PathType Leaf) {
                    Remove-Item -LiteralPath $targetFile
                }
            }
            if (-not $targetAgentsExisted) {
                Remove-EmptyDirectory $targetAgents
            }
            if (-not $targetExisted) {
                Remove-EmptyDirectory $TargetPath
            }
            Write-Output "ROLLBACK_OK"
        }
        throw "Installation failed; previous files were restored. $installError"
    }

    Write-Output "INSTALL_OK"
    Write-Output "target_path=$TargetPath"
    if ($null -ne $backupPath) {
        Write-Output "backup_path=$backupPath"
    }
    else {
        Write-Output "backup_path=none"
    }
}
finally {
    if (Test-Path -LiteralPath $stagingAgentsFile -PathType Leaf) {
        Remove-Item -LiteralPath $stagingAgentsFile
    }
    if (Test-Path -LiteralPath $stagingSkillFile -PathType Leaf) {
        Remove-Item -LiteralPath $stagingSkillFile
    }
    Remove-EmptyDirectory $stagingAgents
    Remove-EmptyDirectory $stagingPath
}
