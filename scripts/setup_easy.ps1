$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")

function Run-Checked([string]$file, [string[]]$cmdArgs) {
  & $file @cmdArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $file $($cmdArgs -join ' ')"
  }
}

function Get-PythonVersion([string]$exe, [string[]]$prefixArgs) {
  try {
    $v = & $exe @prefixArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $v) { return $null }
    $t = "$v".Trim()
    $p = $t.Split(".")
    if ($p.Length -lt 2) { return $null }
    return [PSCustomObject]@{
      Text = $t
      Major = [int]$p[0]
      Minor = [int]$p[1]
    }
  } catch {
    return $null
  }
}

function Resolve-BasePython() {
  # Preferred: Python launcher in descending priority
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    foreach ($ver in @("-3.11", "-3.12", "-3.10", "-3")) {
      $info = Get-PythonVersion "py" @($ver)
      if ($info -and ($info.Major -gt 3 -or ($info.Major -eq 3 -and $info.Minor -ge 10))) {
        return [PSCustomObject]@{ Exe = "py"; PrefixArgs = @($ver); Version = $info.Text }
      }
    }
  }

  # Fallback: scan all python executables on PATH
  $where = Get-Command where.exe -ErrorAction SilentlyContinue
  if ($where) {
    $candidates = & where.exe python 2>$null
    $uniq = @{}
    foreach ($c in $candidates) {
      $path = "$c".Trim()
      if (-not $path) { continue }
      if ($uniq.ContainsKey($path)) { continue }
      $uniq[$path] = $true
      $info = Get-PythonVersion $path @()
      if ($info -and ($info.Major -gt 3 -or ($info.Major -eq 3 -and $info.Minor -ge 10))) {
        return [PSCustomObject]@{ Exe = $path; PrefixArgs = @(); Version = $info.Text }
      }
    }
  }

  # Last fallback: plain python command
  $info2 = Get-PythonVersion "python" @()
  if ($info2 -and ($info2.Major -gt 3 -or ($info2.Major -eq 3 -and $info2.Minor -ge 10))) {
    return [PSCustomObject]@{ Exe = "python"; PrefixArgs = @(); Version = $info2.Text }
  }

  throw "No suitable Python runtime found (requires Python >= 3.10, recommended 3.11)."
}

function Invoke-BasePython([PSCustomObject]$pySpec, [string[]]$cmdArgs) {
  & $pySpec.Exe @($pySpec.PrefixArgs + $cmdArgs)
  if ($LASTEXITCODE -ne 0) {
    throw "Base Python command failed: $($pySpec.Exe) $($pySpec.PrefixArgs + $cmdArgs -join ' ')"
  }
}

$pySpec = Resolve-BasePython

$venv = Join-Path $repo ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
  Invoke-BasePython $pySpec @("-m", "venv", $venv)
}

Run-Checked $venvPy @("-m", "pip", "install", "--upgrade", "pip")
Run-Checked $venvPy @("-m", "pip", "install", "-r", (Join-Path $repo "backend\virtualcell_service\requirements.txt"))
Run-Checked $venvPy @("-m", "pip", "install", "-r", (Join-Path $repo "backend\agent_api\requirements.txt"))
Run-Checked $venvPy @("-m", "pip", "install", "-r", (Join-Path $repo "backend\evidence_service\requirements.txt"))

Write-Host "Setup complete with Python $($pySpec.Version). Next: .\scripts\start_easy.ps1"
