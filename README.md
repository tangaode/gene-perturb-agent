# Gene Perturb Agent

A local web agent for virtual gene KO from user-owned single-cell 10x MTX data.

## Python 版本要求
- Python >= 3.10 (推荐 3.11)
- Python 3.9 会安装失败（如 `uvicorn==0.40.0`）

## 1) Reader Setup (Windows, simplest)
```powershell
git clone https://github.com/<YOUR_ACCOUNT>/gene-perturb-agent.git
cd gene-perturb-agent
.\scripts\setup_easy.ps1
.\scripts\start_easy.ps1
```

首次启动只需输入：
- `MTX_DIR`（用户本地 10x 文件夹）
- `LLM_API_KEY`（仅在你未配置中转 API 时需要）

`MTX_DIR` 需包含：
- `matrix.mtx` 或 `matrix.mtx.gz`
- `features.tsv(.gz)` 或 `genes.tsv(.gz)`
- `barcodes.tsv(.gz)`

然后浏览器打开 `http://localhost:3000`。

## 2) Run in Web UI
输入：
- `TP53`
- `TP53 alpha=0.7 context=default`

## 3) Stop
```powershell
.\scripts\stop_easy.ps1
```

## Optional: pass data path directly
```powershell
.\scripts\start_easy.ps1 -MtxDir "D:/mydata/GSM7831813"
```

## Reconfigure saved local settings
```powershell
.\scripts\configure_easy.ps1
```

## LLM Backends

### A) Relay mode（推荐：用户无需自己的 DeepSeek key）
在 `.env.local` 里设置：
```env
LLM_BACKEND=relay
LLM_BASE_URL=https://your-relay-domain/v1
LLM_MODEL=deepseek-chat
LLM_API_KEY=your-relay-token
```

### B) DeepSeek direct mode
```env
LLM_BACKEND=deepseek
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-...
```

### C) Ollama mode
```env
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:32b
```

## Relay service (cloud)
新增目录：`backend/relay_service`
- `POST /v1/chat/completions`
- `POST /chat/completions`
- `GET /health`

服务端环境变量：
- `DEEPSEEK_API_KEY`（仅保存在云端）
- `RELAY_API_KEY`（给客户端调用中转时使用）
- `RELAY_DEFAULT_MODEL`
- `RELAY_RPM`

## Services and ports (local)
- `agent_api`: `8000`
- `virtualcell_service`: `8001`
- `evidence_service`: `8002`
- `web`: `3000`

## API endpoints (local)
- `POST http://localhost:8000/run`
- `POST http://localhost:8001/perturb`
- `POST http://localhost:8002/verify_batch`

## Evidence sources (12)
NCBI Gene, PubMed, GO:BP, GO:MF, GO:CC, Reactome, KEGG, WikiPathways, MSigDB Hallmark, STRING, BioGRID, CORUM.
