# Gene Perturb Agent

A local web agent for virtual gene KO from user-owned single-cell 10x MTX data.

## 1) Reader Setup (Windows, simplest)
```powershell
git clone https://github.com/<YOUR_ACCOUNT>/gene-perturb-agent.git
cd gene-perturb-agent
.\scripts\setup_easy.ps1
.\scripts\start_easy.ps1
```

At first start, user inputs only:
- `LLM_API_KEY` (DeepSeek API key)
- `MTX_DIR` (their local 10x folder)

The script validates `MTX_DIR` and requires these files:
- `matrix.mtx` or `matrix.mtx.gz`
- `features.tsv(.gz)` or `genes.tsv(.gz)`
- `barcodes.tsv(.gz)`

Then browser opens `http://localhost:3000`.

## 2) Run in Web UI
Input gene in chat box:
- `TP53`
- `TP53 alpha=0.7 context=default`

Output: Top upregulated and downregulated candidates with confidence/evidence-based ranking.

## 3) Stop
```powershell
.\scripts\stop_easy.ps1
```

## Optional: pass data path directly (no prompt)
```powershell
.\scripts\start_easy.ps1 -MtxDir "D:/mydata/GSM7831813" -ApiKey "sk-..."
```

## Reconfigure saved local settings
```powershell
.\scripts\configure_easy.ps1
```

## Services and ports
- `agent_api`: `8000`
- `virtualcell_service`: `8001`
- `evidence_service`: `8002`
- `web`: `3000`

## API endpoints
- `POST http://localhost:8000/run`
- `POST http://localhost:8001/perturb`
- `POST http://localhost:8002/verify_batch`

## LLM backend (default DeepSeek cloud)
Saved in `.env.local`:
- `LLM_BACKEND=deepseek`
- `LLM_BASE_URL=https://api.deepseek.com/v1`
- `LLM_MODEL=deepseek-chat`
- `LLM_API_KEY=...`

Optional Ollama mode:
```env
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:32b
```

## Evidence sources (12)
NCBI Gene, PubMed, GO:BP, GO:MF, GO:CC, Reactome, KEGG, WikiPathways, MSigDB Hallmark, STRING, BioGRID, CORUM.
