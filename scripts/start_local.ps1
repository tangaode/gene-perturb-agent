$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")
$envPath = Join-Path $repo ".env"
$example = Join-Path $repo ".env.example"

if (!(Test-Path $envPath)) {
  Copy-Item $example $envPath
}

$envText = Get-Content $envPath -Raw

function Set-EnvValue([string]$key, [string]$value) {
  $pattern = "^$key=.*$"
  if ($envText -match $pattern) {
    $script:envText = [regex]::Replace($envText, $pattern, "$key=$value", [System.Text.RegularExpressions.RegexOptions]::Multiline)
  } else {
    $script:envText = $envText + "`n$key=$value`n"
  }
}

function Get-EnvValue([string]$key) {
  $m = [regex]::Match($envText, "^$key=(.*)$", [System.Text.RegularExpressions.RegexOptions]::Multiline)
  if ($m.Success) { return $m.Groups[1].Value.Trim() }
  return ""
}

$mtx = Get-EnvValue "MTX_DIR_HOST"
if (-not $mtx) {
  $mtx = Read-Host "Enter local path to 10x MTX folder (e.g. C:/data/GSM7831813)"
}
$cache = Get-EnvValue "VCACHE_DIR_HOST"
if (-not $cache) {
  $cache = Join-Path $repo "cache"
}

# Normalize to forward slashes for Docker on Windows
$mtx = $mtx -replace "\\", "/"
$cache = $cache -replace "\\", "/"

Set-EnvValue "MTX_DIR_HOST" $mtx
Set-EnvValue "VCACHE_DIR_HOST" $cache

$envText | Set-Content -Encoding UTF8 $envPath

Write-Host "Using MTX_DIR_HOST=$mtx"
Write-Host "Using VCACHE_DIR_HOST=$cache"
Write-Host "Starting services..."

Set-Location $repo
& docker compose up --build
