param(
    [string]$DestinationRoot = (Join-Path $env:USERPROFILE ".codex\skills")
)

$source = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $DestinationRoot "varla-gmail-automation"

if (Test-Path -LiteralPath $destination) {
    throw "Destination already exists: $destination. Review it manually before replacing anything."
}

New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $destination -Recurse

Write-Output "Installed skill at: $destination"
Write-Output "Restart Codex so the new skill is discovered."
