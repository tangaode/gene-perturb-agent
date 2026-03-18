param(
  [string]$MtxDir = "",
  [string]$ApiKey = "",
  [string]$Backend = ""
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
    $Backend = "relay"
  }
}

if ([string]::IsNullOrWhiteSpace($MtxDir)) {
  $MtxDir = Read-Host "10x MTX folder path"
}

if ([string]::IsNullOrWhiteSpace($ApiKey) -and ($Backend -eq "deepseek" -or $Backend -eq "openai")) {
  $ApiKey = Read-Host "DeepSeek API key (sk-...)"
}

$map["LLM_BACKEND"] = $Backend
$map["MTX_DIR"] = $MtxDir
if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
  $map["LLM_API_KEY"] = $ApiKey
}

$lines = @()
foreach ($k in ($map.Keys | Sort-Object)) {
  $lines += "$k=$($map[$k])"
}
Set-Content -Encoding UTF8 -Path $envFile -Value $lines

Write-Host "Saved to $envFile"
