param(
  [string]$MtxDir = "",
  [string]$ApiKey = "",
  [string]$Backend = "",
  [string]$BaseUrl = "",
  [string]$Model = ""
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")
$envFile = Join-Path $repo ".env.local"

if (-not (Test-Path $envFile)) {
  New-Item -ItemType File -Path $envFile -Force | Out-Null
}

$map = @{}
foreach ($line in Get-Content $envFile) {
  if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
  $kv = $line.Split('=', 2)
  if ($kv.Length -eq 2) { $map[$kv[0].Trim()] = $kv[1].Trim() }
}

if ([string]::IsNullOrWhiteSpace($Backend)) {
  if ($map.ContainsKey("LLM_BACKEND") -and -not [string]::IsNullOrWhiteSpace($map["LLM_BACKEND"])) {
    $Backend = $map["LLM_BACKEND"]
  } else {
    $Backend = "deepseek"
  }
}
$Backend = $Backend.ToLower()
if (@("deepseek","openai","gemini") -notcontains $Backend) {
  throw "Backend must be one of: deepseek, openai, gemini"
}

if ([string]::IsNullOrWhiteSpace($MtxDir)) {
  $MtxDir = Read-Host "10x MTX folder path"
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
  $ApiKey = Read-Host "API key"
}

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
  if ($Backend -eq "deepseek") { $BaseUrl = "https://api.deepseek.com/v1" }
  elseif ($Backend -eq "openai") { $BaseUrl = "https://api.openai.com/v1" }
  else { $BaseUrl = "https://generativelanguage.googleapis.com/v1beta/openai" }
}

if ([string]::IsNullOrWhiteSpace($Model)) {
  if ($Backend -eq "deepseek") { $Model = "deepseek-chat" }
  elseif ($Backend -eq "openai") { $Model = "gpt-4o-mini" }
  else { $Model = "gemini-2.0-flash" }
}

$map["LLM_BACKEND"] = $Backend
$map["LLM_BASE_URL"] = $BaseUrl
$map["LLM_MODEL"] = $Model
$map["MTX_DIR"] = $MtxDir
$map["LLM_API_KEY"] = $ApiKey

$lines = @()
foreach ($k in ($map.Keys | Sort-Object)) {
  $lines += "$k=$($map[$k])"
}
Set-Content -Encoding UTF8 -Path $envFile -Value $lines

Write-Host "Saved to $envFile"
