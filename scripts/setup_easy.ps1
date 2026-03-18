$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")

function Run-Checked([string]$file, [string[]]$args) {
  & $file @args
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $file $($args -join ' ')"
  }
}

function Get-PythonCmd() {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    & py -3.11 -c "import sys" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
      return @("py", @("-3.11"))
    }
  }
  return @("python", @())
}

$pyCmd = Get-PythonCmd
$pyExe = $pyCmd[0]
$pyPrefixArgs = $pyCmd[1]

$verText = & $pyExe @pyPrefixArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0) {
  throw "Python not found. Please install Python 3.11 first."
}
$parts = $verText.Trim().Split(".")
$major = [int]$parts[0]
$minor = [int]$parts[1]
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
  throw "Python $verText detected. This project requires Python >= 3.10 (recommended 3.11)."
}

$venv = Join-Path $repo ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
  Run-Checked $pyExe (@pyPrefixArgs + @("-m", "venv", $venv))
}

Run-Checked $venvPy @("-m", "pip", "install", "--upgrade", "pip")
Run-Checked $venvPy @("-m", "pip", "install", "-r", (Join-Path $repo "backend\virtualcell_service\requirements.txt"))
Run-Checked $venvPy @("-m", "pip", "install", "-r", (Join-Path $repo "backend\agent_api\requirements.txt"))
Run-Checked $venvPy @("-m", "pip", "install", "-r", (Join-Path $repo "backend\evidence_service\requirements.txt"))

Write-Host "Setup complete with Python $verText. Next: .\scripts\start_easy.ps1"
