param(
  [string]$MtxDir = "",
  [string]$ApiKey = ""
)

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

function Test-MtxDir([string]$dirPath) {
  if ([string]::IsNullOrWhiteSpace($dirPath)) { return $false }
  if (-not (Test-Path $dirPath -PathType Container)) { return $false }

  $hasMatrix = (Test-Path (Join-Path $dirPath "matrix.mtx")) -or (Test-Path (Join-Path $dirPath "matrix.mtx.gz"))
  $hasFeatures = (Test-Path (Join-Path $dirPath "features.tsv")) -or (Test-Path (Join-Path $dirPath "features.tsv.gz")) -or (Test-Path (Join-Path $dirPath "genes.tsv")) -or (Test-Path (Join-Path $dirPath "genes.tsv.gz"))
  $hasBarcodes = (Test-Path (Join-Path $dirPath "barcodes.tsv")) -or (Test-Path (Join-Path $dirPath "barcodes.tsv.gz"))

  return ($hasMatrix -and $hasFeatures -and $hasBarcodes)
}

$envMap = Get-EnvMap $envFile

if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
  $envMap["LLM_API_KEY"] = $ApiKey
}
if (-not [string]::IsNullOrWhiteSpace($MtxDir)) {
  $envMap["MTX_DIR"] = $MtxDir
}

while (-not (Test-MtxDir $envMap["MTX_DIR"])) {
  if ($envMap.ContainsKey("MTX_DIR") -and -not [string]::IsNullOrWhiteSpace($envMap["MTX_DIR"])) {
    Write-Host "Invalid MTX_DIR: $($envMap["MTX_DIR"])" -ForegroundColor Yellow
    Write-Host "Required files: matrix.mtx(.gz), features/genes.tsv(.gz), barcodes.tsv(.gz)" -ForegroundColor Yellow
  }
  $envMap["MTX_DIR"] = Read-Host "Enter local 10x MTX folder (example: D:/scRNA/GSM7831813)"
}

# Defaults for easy mode
if (-not $envMap.ContainsKey("LLM_BACKEND")) { $envMap["LLM_BACKEND"] = "relay" }
if (-not $envMap.ContainsKey("LLM_BASE_URL")) { $envMap["LLM_BASE_URL"] = "http://123.207.10.233:8010/v1" }
if (-not $envMap.ContainsKey("LLM_MODEL")) { $envMap["LLM_MODEL"] = "deepseek-chat" }
if (-not $envMap.ContainsKey("VIRTUALCELL_URL")) { $envMap["VIRTUALCELL_URL"] = "http://localhost:8001" }
if (-not $envMap.ContainsKey("EVIDENCE_URL")) { $envMap["EVIDENCE_URL"] = "http://localhost:8002" }
if (-not $envMap.ContainsKey("VCACHE_DIR")) { $envMap["VCACHE_DIR"] = (Join-Path $repo "cache") }
if (-not $envMap.ContainsKey("VC_N_SUBSAMPLE")) { $envMap["VC_N_SUBSAMPLE"] = "6" }
if (-not $envMap.ContainsKey("VC_N_RUNS")) { $envMap["VC_N_RUNS"] = "6" }
if (-not $envMap.ContainsKey("VC_N_TOP_GENES")) { $envMap["VC_N_TOP_GENES"] = "1800" }
if (-not $envMap.ContainsKey("VC_RETURN_TOPN")) { $envMap["VC_RETURN_TOPN"] = "300" }
if (-not $envMap.ContainsKey("VERIFY_TOPK")) { $envMap["VERIFY_TOPK"] = "5" }
if (-not $envMap.ContainsKey("FINAL_TOPK")) { $envMap["FINAL_TOPK"] = "5" }
if (-not $envMap.ContainsKey("EVIDENCE_TIMEOUT")) { $envMap["EVIDENCE_TIMEOUT"] = "600" }
if (-not $envMap.ContainsKey("VC_ENABLE_CLUSTERING")) { $envMap["VC_ENABLE_CLUSTERING"] = "0" }
if (-not $envMap.ContainsKey("VC_CLUSTER_ANNOTATE")) { $envMap["VC_CLUSTER_ANNOTATE"] = "1" }
if (-not $envMap.ContainsKey("VC_N_CLUSTERS")) { $envMap["VC_N_CLUSTERS"] = "8" }
if (-not $envMap.ContainsKey("VC_CLUSTER_OUT")) { $envMap["VC_CLUSTER_OUT"] = (Join-Path $repo "outputs\\cellgroups") }
if (-not $envMap.ContainsKey("VC_CLUSTER_META")) { $envMap["VC_CLUSTER_META"] = (Join-Path $envMap["VC_CLUSTER_OUT"] "cluster_annotations.csv") }
if (-not $envMap.ContainsKey("NO_PROXY")) { $envMap["NO_PROXY"] = "localhost,127.0.0.1" }

# Ask key only for direct provider mode.
$backend = "$($envMap["LLM_BACKEND"])".ToLower()
if ($backend -eq "relay") {
  $relayUrl = "$($envMap["LLM_BASE_URL"])"
  if ([string]::IsNullOrWhiteSpace($relayUrl) -or $relayUrl -match "your-relay-domain") {
    $envMap["LLM_BASE_URL"] = "http://123.207.10.233:8010/v1"
  }
}
if (($backend -eq "deepseek" -or $backend -eq "openai") -and `
    (-not $envMap.ContainsKey("LLM_API_KEY") -or [string]::IsNullOrWhiteSpace($envMap["LLM_API_KEY"]))) {
  $envMap["LLM_API_KEY"] = Read-Host "Enter DeepSeek API key (sk-...)"
}

if (-not $envMap.ContainsKey("VC_CLUSTER_MODE_SELECTED")) {
  $ans = Read-Host "Enable clustering mode before KO? (Y/N, default N)"
  if ($ans -match '^(y|Y)') { $envMap["VC_ENABLE_CLUSTERING"] = "1" } else { $envMap["VC_ENABLE_CLUSTERING"] = "0" }
  $envMap["VC_CLUSTER_MODE_SELECTED"] = "1"
}

Save-EnvMap $envFile $envMap

# Export env to current process so child processes inherit
foreach ($k in $envMap.Keys) {
  [System.Environment]::SetEnvironmentVariable($k, $envMap[$k], "Process")
}

# Keep module imports simple and portable
$env:PYTHONPATH = $repo.Path

$venvPy = Join-Path $repo ".venv\Scripts\python.exe"
if (Test-Path $venvPy) { $py = $venvPy } else { $py = "python" }

if ($envMap["VC_ENABLE_CLUSTERING"] -eq "1") {
  $clusterOut = $envMap["VC_CLUSTER_OUT"]
  if (-not (Test-Path $clusterOut)) { New-Item -ItemType Directory -Force -Path $clusterOut | Out-Null }
  $meta = $envMap["VC_CLUSTER_META"]
  if (-not (Test-Path $meta)) {
    Write-Host "Preparing cell clustering + UMAP + marker top50..."
    $args = @(
      (Join-Path $repo "scripts\\prepare_cell_groups.py"),
      "--mtx-dir", $envMap["MTX_DIR"],
      "--out-dir", $clusterOut,
      "--top-markers", "50",
      "--n-clusters", $envMap["VC_N_CLUSTERS"]
    )
    if ($envMap["VC_CLUSTER_ANNOTATE"] -eq "1") {
      $args += "--annotate"
    }
    & $py $args
    if ($LASTEXITCODE -ne 0) {
      throw "Cell clustering preparation failed."
    }
    $envMap["VC_CLUSTER_META"] = (Join-Path $clusterOut "cluster_annotations.csv")
    Save-EnvMap $envFile $envMap
  }

  try {
    $ann = Import-Csv $envMap["VC_CLUSTER_META"]
    $groups = $ann | Group-Object cluster, cell_type | Sort-Object Name
    Write-Host "Available groups:"
    foreach ($g in $groups) {
      $parts = $g.Name.Split(",")
      Write-Host ("  cluster:{0} | cell_type:{1} | n={2}" -f $parts[0].Trim(), $parts[1].Trim(), $g.Count)
    }
  } catch {}

  if (-not $envMap.ContainsKey("VC_CELL_GROUP") -or [string]::IsNullOrWhiteSpace($envMap["VC_CELL_GROUP"])) {
    $pick = Read-Host "Pick target group (cluster:<id> or cell_type:<name> or all)"
    if ([string]::IsNullOrWhiteSpace($pick) -or $pick -eq "all") {
      $envMap["VC_CELL_GROUP"] = ""
    } else {
      $envMap["VC_CELL_GROUP"] = $pick
    }
    Save-EnvMap $envFile $envMap
  }
}

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
