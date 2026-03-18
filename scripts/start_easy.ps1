$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")
$runDir = Join-Path $repo "run"
$logDir = Join-Path $repo "logs"
$envFile = Join-Path $repo ".env.local"

New-Item -ItemType Directory -Force -Path $runDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Get-EnvMap([string]$path) {
  $map = @{}
  if (Test-Path $path) {
    foreach ($line in Get-Content $path) {
      if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
      $kv = $line.Split('=', 2)
      if ($kv.Length -eq 2) { $map[$kv[0].Trim()] = $kv[1].Trim() }
    }
  }
  return $map
}

function Save-EnvMap([string]$path, $map) {
  $lines = @()
  foreach ($k in ($map.Keys | Sort-Object)) {
    $lines += "$k=$($map[$k])"
  }
  Set-Content -Encoding UTF8 -Path $path -Value $lines
}

$envMap = Get-EnvMap $envFile

if (-not $envMap.ContainsKey("LLM_API_KEY") -or [string]::IsNullOrWhiteSpace($envMap["LLM_API_KEY"])) {
  $envMap["LLM_API_KEY"] = Read-Host "Enter DeepSeek API key (sk-...)"
}
if (-not $envMap.ContainsKey("MTX_DIR") -or [string]::IsNullOrWhiteSpace($envMap["MTX_DIR"])) {
  $envMap["MTX_DIR"] = Read-Host "Enter local 10x MTX folder (e.g. G:/xunixibao/data/GSM7831813)"
}

# Defaults for easy mode
if (-not $envMap.ContainsKey("LLM_BACKEND")) { $envMap["LLM_BACKEND"] = "deepseek" }
if (-not $envMap.ContainsKey("LLM_BASE_URL")) { $envMap["LLM_BASE_URL"] = "https://api.deepseek.com/v1" }
if (-not $envMap.ContainsKey("LLM_MODEL")) { $envMap["LLM_MODEL"] = "deepseek-chat" }
if (-not $envMap.ContainsKey("VIRTUALCELL_URL")) { $envMap["VIRTUALCELL_URL"] = "http://localhost:8001" }
if (-not $envMap.ContainsKey("EVIDENCE_URL")) { $envMap["EVIDENCE_URL"] = "http://localhost:8002" }
if (-not $envMap.ContainsKey("VCACHE_DIR")) { $envMap["VCACHE_DIR"] = (Join-Path $repo "cache") }
if (-not $envMap.ContainsKey("VC_N_SUBSAMPLE")) { $envMap["VC_N_SUBSAMPLE"] = "6" }
if (-not $envMap.ContainsKey("VC_N_RUNS")) { $envMap["VC_N_RUNS"] = "6" }
if (-not $envMap.ContainsKey("VC_N_TOP_GENES")) { $envMap["VC_N_TOP_GENES"] = "1800" }
if (-not $envMap.ContainsKey("VC_RETURN_TOPN")) { $envMap["VC_RETURN_TOPN"] = "300" }
if (-not $envMap.ContainsKey("VERIFY_TOPK")) { $envMap["VERIFY_TOPK"] = "10" }
if (-not $envMap.ContainsKey("NO_PROXY")) { $envMap["NO_PROXY"] = "localhost,127.0.0.1" }

Save-EnvMap $envFile $envMap

# Export env to current process so child processes inherit
foreach ($k in $envMap.Keys) {
  [System.Environment]::SetEnvironmentVariable($k, $envMap[$k], "Process")
}

$env:PYTHONPATH = "G:\xunixibao\code\_deps;" + $repo.Path

$venvPy = Join-Path $repo ".venv\Scripts\python.exe"
if (Test-Path $venvPy) { $py = $venvPy } else { $py = "python" }

function Start-Service($name, $workdir, $module, $port) {
  $pidFile = Join-Path $runDir "$name.pid"
  $outLog = Join-Path $logDir "$name.out.log"
  $errLog = Join-Path $logDir "$name.err.log"

  if (Test-Path $pidFile) {
    $oldPid = (Get-Content $pidFile -Raw).Trim()
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
      Write-Host "$name already running (PID=$oldPid)"
      return
    }
  }

  $proc = Start-Process -FilePath $py -WorkingDirectory $workdir `
    -ArgumentList "-m uvicorn $module --host 0.0.0.0 --port $port" `
    -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru

  Set-Content -Path $pidFile -Value $proc.Id -Encoding ASCII
  Write-Host "Started $name on :$port (PID=$($proc.Id))"
}

function Start-Web($name, $workdir, $port) {
  $pidFile = Join-Path $runDir "$name.pid"
  $outLog = Join-Path $logDir "$name.out.log"
  $errLog = Join-Path $logDir "$name.err.log"

  if (Test-Path $pidFile) {
    $oldPid = (Get-Content $pidFile -Raw).Trim()
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
      Write-Host "$name already running (PID=$oldPid)"
      return
    }
  }

  $proc = Start-Process -FilePath $py -WorkingDirectory $workdir `
    -ArgumentList "-m http.server $port" `
    -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru

  Set-Content -Path $pidFile -Value $proc.Id -Encoding ASCII
  Write-Host "Started $name on :$port (PID=$($proc.Id))"
}

Start-Service "virtualcell_service" (Join-Path $repo "backend\virtualcell_service") "app.main:app" 8001
Start-Service "evidence_service" (Join-Path $repo "backend\evidence_service") "app.main:app" 8002
Start-Service "agent_api" (Join-Path $repo "backend\agent_api") "app.main:app" 8000
Start-Web "web" (Join-Path $repo "frontend\web") 3000

Write-Host "Waiting for services..."
Start-Sleep -Seconds 3

try {
  Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 10 | Out-Null
  Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 10 | Out-Null
  Invoke-RestMethod -Uri "http://localhost:8002/health" -TimeoutSec 10 | Out-Null
  Write-Host "All services healthy. Opening browser..."
  Start-Process "http://localhost:3000"
} catch {
  Write-Host "Service health check failed. See logs in $logDir"
  throw
}

Write-Host "Done. To stop: .\scripts\stop_easy.ps1"
