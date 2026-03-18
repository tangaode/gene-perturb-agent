$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")
$runDir = Join-Path $repo "run"

if (-not (Test-Path $runDir)) {
  Write-Host "No run directory found."
  exit 0
}

Get-ChildItem -Path $runDir -Filter *.pid | ForEach-Object {
  $name = $_.BaseName
  $procId = (Get-Content $_.FullName -Raw).Trim()
  if ($procId -and (Get-Process -Id $procId -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $procId -Force
    Write-Host "Stopped $name (PID=$procId)"
  } else {
    Write-Host "$name not running"
  }
  Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
}

Write-Host "Done."
