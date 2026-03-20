# Gene Perturb Agent

Local-first virtual gene perturbation agent for 10x single-cell MTX datasets.

## Requirements
- Windows 10/11
- Python 3.10+
- Internet access to the selected LLM provider endpoint

## Quick Start (PowerShell)
```powershell
git clone https://github.com/tangaode/gene-perturb-agent.git
cd gene-perturb-agent
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_easy.ps1
.\scripts\start_easy.ps1
```

## Input Data
`MTX_DIR` supports:
- A single 10x folder containing `matrix.mtx(.gz)`, `features.tsv(.gz)`/`genes.tsv(.gz)`, and `barcodes.tsv(.gz)`.
- A parent folder containing multiple 10x sample folders (recursive discovery). All detected samples are merged by union gene space; barcodes are prefixed by sample folder name.

## Clustering and Cell-Group Selection
When clustering mode is enabled, the launcher performs:
1. Cell clustering and UMAP projection.
2. Top-50 marker extraction per cluster.
3. LLM-based cluster label suggestion.
4. Optional manual label override in PowerShell.
5. Target group selection by `cluster:<id>` or `cell_type:<name>`.

## Clustering Outputs
Default output directory: `outputs/cellgroups/`

Generated files:
- `cluster_annotations.csv`: barcode-level cluster and cell-type labels.
- `umap_coords.csv`: UMAP coordinates.
- `umap_clusters_unannotated.png`: UMAP colored by raw cluster IDs.
- `umap_clusters_annotated.png`: UMAP colored by final cell-type labels.
- `umap_clusters.png`: alias of the annotated UMAP for backward compatibility.
- `cluster_markers_top50.json`: Top-50 marker genes per cluster.
- `cluster_markers_top50.csv`: marker table with `cluster`, `rank`, `gene`, `log2fc`, `mean_in`, and `mean_out`.

## LLM Provider Configuration
`start_easy.ps1` prompts for provider selection on each launch:
- `deepseek`: asks for base URL, model, and API key.
- `openai`: asks for base URL, model, and API key.
- `qwen`: asks for base URL, model, and API key (OpenAI-compatible endpoint).

For `deepseek/openai/qwen`, an API key is required.

Typical base URLs:
- DeepSeek: `https://api.deepseek.com/v1`
- OpenAI: `https://api.openai.com/v1`
- Qwen (DashScope compatible mode): `https://dashscope.aliyuncs.com/compatible-mode/v1`

## Prediction Output
Default final output is Top-5 upregulated and Top-5 downregulated genes (`FINAL_TOPK=5`).

## One-Click Package
Build:
```powershell
.\scripts\build_release.ps1
```

Package:
- `release/GenePerturbAgent.zip`

End-user flow:
1. Unzip `GenePerturbAgent.zip`.
2. Run `Run-Agent.bat`.
3. Select `MTX_DIR` at startup (press Enter to reuse last path).
4. Optionally run clustering and select a cell group.
5. Open `http://localhost:3000`.

Notes:
- `start_easy.ps1` prompts for the dataset path on every startup.
- If `MTX_DIR` changes, clustering outputs are regenerated for the new dataset and cell-group selection is requested again.

## Local Services / Ports
- `agent_api`: `8000`
- `virtualcell_service`: `8001`
- `evidence_service`: `8002`
- `web`: `3000`

## Evidence Sources
NCBI Gene, PubMed, GO:BP, GO:MF, GO:CC, Reactome, KEGG, WikiPathways, MSigDB Hallmark, STRING, BioGRID, CORUM.
