$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")

$env:PYTHONPATH = "G:\xunixibao\code\_deps;" + $repo.Path

# Configure endpoints
$env:VIRTUALCELL_URL = "http://localhost:8001"
$env:EVIDENCE_URL = "http://localhost:8002"
$env:LLM_BACKEND = "deepseek"
if (-not $env:LLM_BASE_URL) { $env:LLM_BASE_URL = "https://api.deepseek.com/v1" }
if (-not $env:LLM_MODEL) { $env:LLM_MODEL = "deepseek-chat" }
if (-not $env:LLM_API_KEY) {
  $env:LLM_API_KEY = Read-Host "Enter DeepSeek API key (sk-...)"
}

# Keep Ollama vars for compatibility (optional fallback)
$ollama = $env:OLLAMA_BASE_URL
if (-not $ollama) { $ollama = "http://localhost:11434" }
$env:OLLAMA_BASE_URL = $ollama
if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "deepseek-r1:32b" }
$env:NO_PROXY = "localhost,127.0.0.1"

# quick defaults for interactive use (adjust as needed)
if (-not $env:VC_N_SUBSAMPLE) { $env:VC_N_SUBSAMPLE = "5" }
if (-not $env:VC_N_RUNS) { $env:VC_N_RUNS = "5" }
if (-not $env:VC_N_TOP_GENES) { $env:VC_N_TOP_GENES = "1500" }
if (-not $env:VC_RETURN_TOPN) { $env:VC_RETURN_TOPN = "300" }

# VirtualCell data/cache paths
if (-not $env:MTX_DIR) {
  $env:MTX_DIR = Read-Host "Enter local path to 10x MTX folder (e.g. G:/xunixibao/data/GSM7831813)"
}
if (-not $env:VCACHE_DIR) {
  $env:VCACHE_DIR = (Join-Path $repo "cache")
}

# Start services in separate windows
$vc = "python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
$ev = "python -m uvicorn app.main:app --host 0.0.0.0 --port 8002"
$ag = "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
$web = "python -m http.server 3000"

Start-Process -WorkingDirectory (Join-Path $repo "backend\virtualcell_service") -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $vc
Start-Process -WorkingDirectory (Join-Path $repo "backend\evidence_service") -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $ev
Start-Process -WorkingDirectory (Join-Path $repo "backend\agent_api") -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $ag
Start-Process -WorkingDirectory (Join-Path $repo "frontend\web") -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $web

Write-Host "Services started. Open http://localhost:3000"
