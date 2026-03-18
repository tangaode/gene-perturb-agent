$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")

$venv = Join-Path $repo ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
  python -m venv $venv
}

& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r (Join-Path $repo "backend\virtualcell_service\requirements.txt")
& $venvPy -m pip install -r (Join-Path $repo "backend\agent_api\requirements.txt")
& $venvPy -m pip install -r (Join-Path $repo "backend\evidence_service\requirements.txt")

Write-Host "Setup complete. Next: .\scripts\start_easy.ps1"
