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

  function Is-TenXFolder([string]$p) {
    $hasMatrix = (Test-Path (Join-Path $p "matrix.mtx")) -or (Test-Path (Join-Path $p "matrix.mtx.gz"))
    $hasFeatures = (Test-Path (Join-Path $p "features.tsv")) -or (Test-Path (Join-Path $p "features.tsv.gz")) -or (Test-Path (Join-Path $p "genes.tsv")) -or (Test-Path (Join-Path $p "genes.tsv.gz"))
    $hasBarcodes = (Test-Path (Join-Path $p "barcodes.tsv")) -or (Test-Path (Join-Path $p "barcodes.tsv.gz"))
    return ($hasMatrix -and $hasFeatures -and $hasBarcodes)
  }

  if (Is-TenXFolder $dirPath) { return $true }

  $sampleDirs = Get-ChildItem -Path $dirPath -Directory -Recurse -ErrorAction SilentlyContinue |
    Where-Object { Is-TenXFolder $_.FullName } |
    Select-Object -First 1
  return ($null -ne $sampleDirs)
}

$envMap = Get-EnvMap $envFile

if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
  $envMap["LLM_API_KEY"] = $ApiKey
}
if (-not [string]::IsNullOrWhiteSpace($MtxDir)) {
  $envMap["MTX_DIR"] = $MtxDir
}

$curMtx = ""
if ($envMap.ContainsKey("MTX_DIR")) { $curMtx = "$($envMap["MTX_DIR"])" }
$mtxPromptDefault = if ([string]::IsNullOrWhiteSpace($curMtx)) { "none" } else { $curMtx }
$inputMtx = Read-Host "MTX folder (single sample or parent folder with multiple samples) [default: $mtxPromptDefault]"
if (-not [string]::IsNullOrWhiteSpace($inputMtx)) {
  $envMap["MTX_DIR"] = $inputMtx
}
while (-not (Test-MtxDir $envMap["MTX_DIR"])) {
  if ($envMap.ContainsKey("MTX_DIR") -and -not [string]::IsNullOrWhiteSpace($envMap["MTX_DIR"])) {
    Write-Host "Invalid MTX_DIR: $($envMap["MTX_DIR"])" -ForegroundColor Yellow
    Write-Host "Required files: matrix.mtx(.gz), features/genes.tsv(.gz), barcodes.tsv(.gz), or a parent folder containing such sample folders." -ForegroundColor Yellow
  }
  $envMap["MTX_DIR"] = Read-Host "Enter local 10x MTX folder"
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
if (-not $envMap.ContainsKey("VERIFY_TOPK")) { $envMap["VERIFY_TOPK"] = "5" }
if (-not $envMap.ContainsKey("FINAL_TOPK")) { $envMap["FINAL_TOPK"] = "5" }
if (-not $envMap.ContainsKey("EVIDENCE_TIMEOUT")) { $envMap["EVIDENCE_TIMEOUT"] = "600" }
if (-not $envMap.ContainsKey("VC_ENABLE_CLUSTERING")) { $envMap["VC_ENABLE_CLUSTERING"] = "0" }
if (-not $envMap.ContainsKey("VC_CLUSTER_ANNOTATE")) { $envMap["VC_CLUSTER_ANNOTATE"] = "1" }
if (-not $envMap.ContainsKey("VC_N_CLUSTERS")) { $envMap["VC_N_CLUSTERS"] = "8" }
if (-not $envMap.ContainsKey("VC_CLUSTER_OUT")) { $envMap["VC_CLUSTER_OUT"] = (Join-Path $repo "outputs\\cellgroups") }
if (-not $envMap.ContainsKey("VC_CLUSTER_META")) { $envMap["VC_CLUSTER_META"] = (Join-Path $envMap["VC_CLUSTER_OUT"] "cluster_annotations.csv") }
if (-not $envMap.ContainsKey("NO_PROXY")) { $envMap["NO_PROXY"] = "localhost,127.0.0.1" }

# LLM provider selection on each launch (3 providers only).
$prevProvider = "$($envMap["LLM_BACKEND"])".ToLower()
if ([string]::IsNullOrWhiteSpace($prevProvider)) { $prevProvider = "deepseek" }
$allowedProviders = @("deepseek", "openai", "qwen")
if ($allowedProviders -notcontains $prevProvider) { $prevProvider = "deepseek" }
$provider = (Read-Host "LLM provider (deepseek/openai/qwen) [default: $prevProvider]").Trim().ToLower()
if ([string]::IsNullOrWhiteSpace($provider)) { $provider = $prevProvider }

if ($provider -eq "deepseek") {
  $envMap["LLM_BACKEND"] = "deepseek"
  $baseDefault = if ([string]::IsNullOrWhiteSpace($envMap["LLM_BASE_URL"])) { "https://api.deepseek.com/v1" } else { $envMap["LLM_BASE_URL"] }
  $baseIn = Read-Host "DeepSeek base URL [default: $baseDefault]"
  $envMap["LLM_BASE_URL"] = if ([string]::IsNullOrWhiteSpace($baseIn)) { $baseDefault } else { $baseIn }
  $modelDefault = if ([string]::IsNullOrWhiteSpace($envMap["LLM_MODEL"])) { "deepseek-chat" } else { $envMap["LLM_MODEL"] }
  $modelIn = Read-Host "DeepSeek model [default: $modelDefault]"
  $envMap["LLM_MODEL"] = if ([string]::IsNullOrWhiteSpace($modelIn)) { $modelDefault } else { $modelIn }
  $keyIn = Read-Host "DeepSeek API key (sk-...) [press Enter to keep current]"
  if (-not [string]::IsNullOrWhiteSpace($keyIn)) { $envMap["LLM_API_KEY"] = $keyIn }
}
elseif ($provider -eq "openai") {
  $envMap["LLM_BACKEND"] = "openai"
  $baseDefault = if ([string]::IsNullOrWhiteSpace($envMap["LLM_BASE_URL"])) { "https://api.openai.com/v1" } else { $envMap["LLM_BASE_URL"] }
  $baseIn = Read-Host "OpenAI base URL [default: $baseDefault]"
  $envMap["LLM_BASE_URL"] = if ([string]::IsNullOrWhiteSpace($baseIn)) { $baseDefault } else { $baseIn }
  $modelDefault = if ([string]::IsNullOrWhiteSpace($envMap["LLM_MODEL"])) { "gpt-4o-mini" } else { $envMap["LLM_MODEL"] }
  $modelIn = Read-Host "OpenAI model [default: $modelDefault]"
  $envMap["LLM_MODEL"] = if ([string]::IsNullOrWhiteSpace($modelIn)) { $modelDefault } else { $modelIn }
  $keyIn = Read-Host "OpenAI API key [press Enter to keep current]"
  if (-not [string]::IsNullOrWhiteSpace($keyIn)) { $envMap["LLM_API_KEY"] = $keyIn }
}
elseif ($provider -eq "qwen") {
  $envMap["LLM_BACKEND"] = "qwen"
  $baseDefault = "https://dashscope.aliyuncs.com/compatible-mode/v1"
  $baseIn = Read-Host "Qwen base URL [default: $baseDefault]"
  $envMap["LLM_BASE_URL"] = if ([string]::IsNullOrWhiteSpace($baseIn)) { $baseDefault } else { $baseIn }
  $modelDefault = if ([string]::IsNullOrWhiteSpace($envMap["LLM_MODEL"])) { "qwen-plus" } else { $envMap["LLM_MODEL"] }
  $modelIn = Read-Host "Qwen model [default: $modelDefault]"
  $envMap["LLM_MODEL"] = if ([string]::IsNullOrWhiteSpace($modelIn)) { $modelDefault } else { $modelIn }
  $keyIn = Read-Host "Qwen API key [press Enter to keep current]"
  if (-not [string]::IsNullOrWhiteSpace($keyIn)) { $envMap["LLM_API_KEY"] = $keyIn }
}
else {
  throw "Unsupported provider: $provider. Use deepseek/openai/qwen."
}

if (($envMap["LLM_BACKEND"] -eq "deepseek" -or $envMap["LLM_BACKEND"] -eq "openai" -or $envMap["LLM_BACKEND"] -eq "qwen") -and `
    (-not $envMap.ContainsKey("LLM_API_KEY") -or [string]::IsNullOrWhiteSpace($envMap["LLM_API_KEY"]))) {
  throw "LLM_API_KEY is required for provider $($envMap["LLM_BACKEND"])."
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
  $lastMtx = ""
  if ($envMap.ContainsKey("VC_CLUSTER_SOURCE_MTX_DIR")) { $lastMtx = "$($envMap["VC_CLUSTER_SOURCE_MTX_DIR"])" }
  $currentMtx = "$($envMap["MTX_DIR"])"
  $mtxChanged = ($lastMtx -ne $currentMtx)
  if ($mtxChanged) {
    $envMap["VC_CELL_GROUP"] = ""
  }

  if ($mtxChanged -or -not (Test-Path $meta)) {
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
    $prepOutput = & $py $args
    if ($LASTEXITCODE -ne 0) {
      throw "Cell clustering preparation failed."
    }
    if ($prepOutput) {
      try {
        $summary = ($prepOutput | Select-Object -Last 1 | ConvertFrom-Json)
        if ($summary) {
          Write-Host "Clustering output folder: $($summary.out_dir)"
        }
      } catch {}
    }
    $envMap["VC_CLUSTER_META"] = (Join-Path $clusterOut "cluster_annotations.csv")
    $envMap["VC_CLUSTER_SOURCE_MTX_DIR"] = $currentMtx
    Save-EnvMap $envFile $envMap
  }

  try {
    $ann = Import-Csv $envMap["VC_CLUSTER_META"]
    $clusterTable = $ann | Group-Object cluster, cell_type | Sort-Object Name
    Write-Host "LLM cluster annotation suggestions:"
    foreach ($g in $clusterTable) {
      $parts = $g.Name.Split(",")
      Write-Host ("  cluster {0}: {1} (n={2})" -f $parts[0].Trim(), $parts[1].Trim(), $g.Count)
    }

    $labelMode = (Read-Host "Label mode: keep_llm / custom (default keep_llm)").Trim().ToLower()
    if ([string]::IsNullOrWhiteSpace($labelMode)) { $labelMode = "keep_llm" }
    if ($labelMode -ne "keep_llm" -and $labelMode -ne "custom") {
      Write-Host "Unknown label mode: $labelMode . Using keep_llm."
      $labelMode = "keep_llm"
    }

    if ($labelMode -eq "custom") {
      $byCluster = $ann | Group-Object cluster | Sort-Object Name
      foreach ($cg in $byCluster) {
        $cid = "$($cg.Name)"
        $current = ($cg.Group | Select-Object -First 1).cell_type
        $newName = Read-Host "Cluster $cid label [$current]"
        if (-not [string]::IsNullOrWhiteSpace($newName)) {
          foreach ($row in $ann) {
            if ("$($row.cluster)" -eq $cid) { $row.cell_type = $newName }
          }
        }
      }
      $ann | Export-Csv -Path $envMap["VC_CLUSTER_META"] -NoTypeInformation -Encoding UTF8
      Write-Host "Updated cluster annotations saved: $($envMap["VC_CLUSTER_META"])"
    }
  } catch {}

  $currentGroup = ""
  if ($envMap.ContainsKey("VC_CELL_GROUP")) { $currentGroup = "$($envMap["VC_CELL_GROUP"])" }
  $defaultHint = if ([string]::IsNullOrWhiteSpace($currentGroup)) { "all" } else { $currentGroup }
  $pick = Read-Host "Pick target group (cluster:<id>, cell_type:<name>, or all) [default: $defaultHint]"
  if ([string]::IsNullOrWhiteSpace($pick)) { $pick = $defaultHint }
  if ($pick -eq "all") {
    $envMap["VC_CELL_GROUP"] = ""
  } else {
    $envMap["VC_CELL_GROUP"] = $pick
  }
  Save-EnvMap $envFile $envMap
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
