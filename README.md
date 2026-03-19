# Gene Perturb Agent

A local-first virtual gene perturbation agent for 10x single-cell MTX data.

## Requirements
- Windows 10/11
- Python 3.10+ (recommended 3.11)
- Internet access to your relay endpoint

## Quick Start (PowerShell)
```powershell
git clone https://github.com/<YOUR_ACCOUNT>/gene-perturb-agent.git
cd gene-perturb-agent
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_easy.ps1
.\scripts\start_easy.ps1
```

On first run, provide only:
- `MTX_DIR` (local 10x folder)
The relay endpoint is preconfigured to `http://123.207.10.233:8010/v1`.

Open `http://localhost:3000` and enter a gene symbol (e.g. `TP53`). The UI returns Top 5 upregulated and Top 5 downregulated genes by default.

## Relay Configuration (No User API Key)
Set in `.env.local`:
```env
LLM_BACKEND=relay
LLM_BASE_URL=http://123.207.10.233:8010/v1
LLM_MODEL=deepseek-chat
LLM_API_KEY=
```

## Input Data Format
`MTX_DIR` must contain:
- `matrix.mtx` or `matrix.mtx.gz`
- `features.tsv(.gz)` or `genes.tsv(.gz)`
- `barcodes.tsv(.gz)`

## Stop Services
```powershell
.\scripts\stop_easy.ps1
```

## One-Click Package (No Git for end users)
Build package:
```powershell
.\scripts\build_release.ps1
```
Output: `release/GenePerturbAgent.zip`

End user flow:
1. Unzip `GenePerturbAgent.zip`
2. Double-click `Run-Agent.bat`
3. Enter local `MTX_DIR` when prompted
4. Use the web UI at `http://localhost:3000`

Optional launchers:
- `Configure-Agent.bat`
- `Stop-Agent.bat`

## Local Services / Ports
- `agent_api`: `8000`
- `virtualcell_service`: `8001`
- `evidence_service`: `8002`
- `web`: `3000`

## Local API Endpoints
- `POST http://localhost:8000/run`
- `POST http://localhost:8001/perturb`
- `POST http://localhost:8002/verify_batch`

## Evidence Sources
NCBI Gene, PubMed, GO:BP, GO:MF, GO:CC, Reactome, KEGG, WikiPathways, MSigDB Hallmark, STRING, BioGRID, CORUM.


Set FINAL_TOPK in .env.local to change the final number of genes returned.

