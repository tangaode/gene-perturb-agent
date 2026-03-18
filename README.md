# Gene Perturb Agent

## Quick Start (for readers, Windows)
1. Open PowerShell and run:
```powershell
cd G:\xunixibao\code\gene-perturb-agent
.\scripts\setup_easy.ps1
.\scripts\start_easy.ps1
```
2. First run asks only:
- `LLM_API_KEY` (DeepSeek key)
- `MTX_DIR` (local 10x MTX folder, e.g. `G:/xunixibao/data/GSM7831813`)
3. Browser opens `http://localhost:3000`.
4. Enter gene (example: `TP53` or `TP53 alpha=0.7 context=default`).

Stop services:
```powershell
.\scripts\stop_easy.ps1
```

## One-click launcher
Double-click `start_agent.bat` (after running setup once).

## What user needs to do
- Input only gene symbol in web chat.
- Backend automatically runs virtual KO model + evidence verification + LLM reranking.

## Ports
- `agent_api`: 8000
- `virtualcell_service`: 8001
- `evidence_service`: 8002
- `web`: 3000

## API endpoints
- `POST http://localhost:8000/run`
- `POST http://localhost:8001/perturb`
- `POST http://localhost:8002/verify_batch`

## DeepSeek cloud mode (default)
Configured in `.env.local` by `start_easy.ps1`:
- `LLM_BACKEND=deepseek`
- `LLM_BASE_URL=https://api.deepseek.com/v1`
- `LLM_MODEL=deepseek-chat`
- `LLM_API_KEY=...`

## Optional Ollama mode
Set in `.env.local`:
```env
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:32b
```

## Evidence Sources (12)
1. NCBI Gene
2. PubMed (E-utils)
3. GO:BP (Enrichr)
4. GO:MF (Enrichr)
5. GO:CC (Enrichr)
6. Reactome (Enrichr)
7. KEGG (Enrichr)
8. WikiPathways (Enrichr)
9. MSigDB Hallmark (Enrichr)
10. STRING
11. BioGRID
12. CORUM
