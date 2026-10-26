$ErrorActionPreference = "Stop"

$SkillRoot = Split-Path -Parent $PSScriptRoot
$Required = @(
  "SKILL.md",
  "references\ONE_FILE_GUIDE.md"
)

foreach ($item in $Required) {
  $path = Join-Path $SkillRoot $item
  if (-not (Test-Path -LiteralPath $path)) {
    throw "Missing required file: $item"
  }
}

$skill = Get-Content -LiteralPath (Join-Path $SkillRoot "SKILL.md") -Encoding UTF8 -Raw
if ($skill -notmatch "name:\s*varla-kol-reply-assistant") {
  throw "SKILL.md frontmatter is missing the expected skill name."
}
if ($skill -notmatch "1-3 days") {
  throw "SKILL.md is missing the current 1-3 day shipping rule."
}

$guide = Get-Content -LiteralPath (Join-Path $SkillRoot "references\ONE_FILE_GUIDE.md") -Encoding UTF8 -Raw
if ($guide -notmatch "support@varlascooter.com" -or $guide -notmatch "customer@varlascooter.com") {
  throw "Guide is missing support/customer email rules."
}

"OK: skill package files are valid."
