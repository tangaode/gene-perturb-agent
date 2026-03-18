$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")
$releaseRoot = Join-Path $repo "release"
$pkgName = "GenePerturbAgent"
$pkgDir = Join-Path $releaseRoot $pkgName
$zipPath = Join-Path $releaseRoot "$pkgName.zip"

if (Test-Path $pkgDir) { Remove-Item -Recurse -Force $pkgDir }
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }

New-Item -ItemType Directory -Force -Path $pkgDir | Out-Null

$copyItems = @(
  "backend",
  "frontend",
  "scripts",
  "README.md",
  ".env.example",
  "Run-Agent.bat",
  "Stop-Agent.bat",
  "Configure-Agent.bat"
)

foreach ($item in $copyItems) {
  $src = Join-Path $repo $item
  if (Test-Path $src) {
    Copy-Item -Path $src -Destination $pkgDir -Recurse -Force
  }
}

# clean runtime artifacts from package
@(".venv", "logs", "run", "cache", ".env.local") | ForEach-Object {
  $p = Join-Path $pkgDir $_
  if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}

Compress-Archive -Path (Join-Path $pkgDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "Release package generated: $zipPath"
