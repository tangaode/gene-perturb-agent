# Gene Perturb Agent

A local-first virtual gene perturbation agent for 10x single-cell MTX data.

## Requirements
- Windows 10/11
- Python 3.10+ (recommended 3.11)
- Internet access to relay endpoint for LLM calls

## Quick Start (PowerShell)
```powershell
git clone https://github.com/<YOUR_ACCOUNT>/gene-perturb-agent.git
cd gene-perturb-agent
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_easy.ps1
.\scripts\start_easy.ps1
```

## Built-in Clustering Workflow
When starting, launcher can enable clustering mode:
1. Run local clustering on single-cell matrix
2. Export UMAP figure to output folder
3. Extract Top50 marker genes per cluster
4. Use LLM to assign cell-type labels to clusters (optional)
5. Ask user to select target group (`cluster:<id>` or `cell_type:<name>`)
6. Run KO only on selected cell group

Generated files:
- `outputs/cellgroups/umap_clusters.png`
- `outputs/cellgroups/cluster_annotations.csv`
- `outputs/cellgroups/cluster_markers_top50.json`

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

## Outputs
Default final output: Top 5 upregulated + Top 5 downregulated genes (`FINAL_TOPK=5`).

## One-Click Package (No Git for end users)
Build package:
```powershell
.\scripts\build_release.ps1
```
Output: `release/GenePerturbAgent.zip`

End user flow:
1. Unzip `GenePerturbAgent.zip`
2. Double-click `Run-Agent.bat`
3. Enter local `MTX_DIR`
4. (Optional) enable clustering and select cell group
5. Use web UI at `http://localhost:3000`

Optional launchers:
- `Configure-Agent.bat`
- `Stop-Agent.bat`

## Local Services / Ports
- `agent_api`: `8000`
- `virtualcell_service`: `8001`
- `evidence_service`: `8002`
- `web`: `3000`

## Evidence Sources
NCBI Gene, PubMed, GO:BP, GO:MF, GO:CC, Reactome, KEGG, WikiPathways, MSigDB Hallmark, STRING, BioGRID, CORUM.
