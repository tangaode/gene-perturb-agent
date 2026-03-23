import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc
from scipy import sparse


def _build_adata(
    X: sparse.csr_matrix,
    genes: List[str],
    barcodes: List[str],
) -> ad.AnnData:
    adata = ad.AnnData(X=X.copy())
    adata.var_names = pd.Index([str(g) for g in genes])
    adata.obs_names = pd.Index([str(b) for b in barcodes])
    adata.var_names_make_unique()
    adata.obs_names_make_unique()
    adata.obs["sample"] = [b.split(":", 1)[0] if ":" in b else "sample_0" for b in adata.obs_names]
    adata.obs["barcode"] = adata.obs_names.astype(str)
    return adata


def _apply_qc(
    adata: ad.AnnData,
    min_genes: int = 200,
    max_genes: int = 8000,
    min_counts: int = 500,
    max_pct_mt: float = 20.0,
    max_pct_ribo: float = 60.0,
    min_cells_per_gene: int = 3,
) -> pd.DataFrame:
    gene_upper = adata.var_names.str.upper()
    adata.var["mt"] = gene_upper.str.startswith("MT-")
    adata.var["ribo"] = gene_upper.str.startswith("RPL") | gene_upper.str.startswith("RPS")

    sc.pp.calculate_qc_metrics(
        adata,
        qc_vars=["mt", "ribo"],
        percent_top=None,
        log1p=False,
        inplace=True,
    )

    n_cells_before = int(adata.n_obs)
    n_genes_before = int(adata.n_vars)

    mask = (
        (adata.obs["n_genes_by_counts"] >= min_genes)
        & (adata.obs["n_genes_by_counts"] <= max_genes)
        & (adata.obs["total_counts"] >= min_counts)
        & (adata.obs["pct_counts_mt"] <= max_pct_mt)
        & (adata.obs["pct_counts_ribo"] <= max_pct_ribo)
    )
    adata._inplace_subset_obs(mask.to_numpy())
    sc.pp.filter_genes(adata, min_cells=min_cells_per_gene)

    summary = pd.DataFrame(
        [
            {"metric": "n_cells_before", "value": n_cells_before},
            {"metric": "n_cells_after", "value": int(adata.n_obs)},
            {"metric": "n_genes_before", "value": n_genes_before},
            {"metric": "n_genes_after", "value": int(adata.n_vars)},
            {"metric": "min_genes", "value": min_genes},
            {"metric": "max_genes", "value": max_genes},
            {"metric": "min_counts", "value": min_counts},
            {"metric": "max_pct_mt", "value": max_pct_mt},
            {"metric": "max_pct_ribo", "value": max_pct_ribo},
            {"metric": "min_cells_per_gene", "value": min_cells_per_gene},
        ]
    )
    return summary


def cluster_cells(
    X: sparse.csr_matrix,
    genes: List[str],
    barcodes: List[str],
    n_pcs: int = 30,
    n_top_genes: int = 2000,
    resolution: float = 0.5,
    random_state: int = 42,
):
    adata = _build_adata(X, genes, barcodes)
    qc_summary = _apply_qc(adata)

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    adata.raw = adata.copy()

    sc.pp.highly_variable_genes(
        adata,
        n_top_genes=min(n_top_genes, adata.n_vars),
        flavor="seurat",
        subset=True,
    )
    sc.pp.scale(adata, max_value=10, zero_center=False)
    sc.tl.pca(adata, use_highly_variable=True, svd_solver="arpack", zero_center=False)

    use_harmony = adata.obs["sample"].nunique() > 1
    rep = "X_pca"
    if use_harmony:
        try:
            sc.external.pp.harmony_integrate(adata, "sample")
            rep = "X_pca_harmony"
        except Exception:
            rep = "X_pca"

    sc.pp.neighbors(adata, use_rep=rep, n_pcs=n_pcs)
    sc.tl.umap(adata, random_state=random_state)
    sc.tl.leiden(adata, flavor="igraph", n_iterations=2, resolution=resolution, key_added="cluster")

    labels = adata.obs["cluster"].astype(int).to_numpy()
    pcs = adata.obsm[rep] if rep in adata.obsm else adata.obsm["X_pca"]
    Xn = adata.X
    return labels, pcs, Xn, adata, qc_summary


def _is_valid_marker_gene(gene: str) -> bool:
    g = gene.upper()
    linc_like = (
        g.startswith("LINC")
        or g.startswith("MIR")
        or g.startswith("SNORA")
        or g.startswith("SNORD")
        or g.startswith("RNU")
        or g.startswith("MT-")
    )
    if linc_like:
        return False
    # common Ensembl-style lnc aliases and clone-like symbols
    if re.match(r"^(AC|AL)\d+\.\d+$", g):
        return False
    return True


def compute_top_markers(
    adata: ad.AnnData,
    llm_top_n: int = 100,
    sig_p_cutoff: float = 0.05,
    sig_logfc_cutoff: float = 0.5,
) -> Tuple[Dict[int, List[str]], pd.DataFrame]:
    sc.tl.rank_genes_groups(
        adata,
        groupby="cluster",
        method="wilcoxon",
        n_genes=min(max(500, llm_top_n * 5), adata.n_vars),
        pts=True,
    )

    rows = []
    markers_for_llm: Dict[int, List[str]] = {}
    clusters = sorted(adata.obs["cluster"].astype(int).unique().tolist())
    for c in clusters:
        df = sc.get.rank_genes_groups_df(adata, group=str(c)).copy()
        if df.empty:
            markers_for_llm[int(c)] = []
            continue

        df = df.sort_values(["pvals_adj", "pvals", "logfoldchanges"], ascending=[True, True, False])
        df = df[df["logfoldchanges"] > 0]
        if "names" in df.columns:
            df = df.rename(columns={"names": "gene"})
        if "pvals_adj" not in df.columns:
            df["pvals_adj"] = np.nan
        if "pvals" not in df.columns:
            df["pvals"] = np.nan

        df["gene"] = df["gene"].astype(str)
        df["valid_gene"] = df["gene"].map(_is_valid_marker_gene)
        df_valid = df[df["valid_gene"]].copy()
        if df_valid.empty:
            df_valid = df.copy()

        p_for_filter = df_valid["pvals_adj"].fillna(df_valid["pvals"])
        sig = df_valid[(p_for_filter < sig_p_cutoff) & (df_valid["logfoldchanges"] > sig_logfc_cutoff)].copy()
        sig = sig.sort_values(["pvals_adj", "pvals", "logfoldchanges"], ascending=[True, True, False])

        if not sig.empty:
            sig["cluster"] = int(c)
            sig["rank"] = np.arange(1, len(sig) + 1)
            rows.append(
                sig[["cluster", "rank", "gene", "logfoldchanges", "pvals", "pvals_adj"]]
                .rename(columns={"logfoldchanges": "log2fc"})
                .reset_index(drop=True)
            )

        llm_source = sig if not sig.empty else df_valid
        markers_for_llm[int(c)] = llm_source["gene"].head(llm_top_n).tolist()

    marker_table = pd.concat(rows, axis=0, ignore_index=True) if rows else pd.DataFrame(
        columns=["cluster", "rank", "gene", "log2fc", "pvals", "pvals_adj"]
    )
    return markers_for_llm, marker_table


def run_umap(adata: ad.AnnData):
    if "X_umap" not in adata.obsm:
        raise ValueError("X_umap not found in AnnData")
    return adata.obsm["X_umap"]


def save_outputs(
    out_dir: str,
    adata: ad.AnnData,
    labels: np.ndarray,
    umap_xy: np.ndarray,
    markers: Dict[int, List[str]],
    marker_table: pd.DataFrame,
    cell_type_map: Dict[int, str],
    qc_summary: pd.DataFrame,
):
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)

    ann = pd.DataFrame(
        {
            "barcode": adata.obs["barcode"].astype(str).tolist(),
            "sample": adata.obs["sample"].astype(str).tolist(),
            "cluster": labels.astype(int),
            "cell_type": [cell_type_map.get(int(c), f"cluster_{int(c)}") for c in labels],
            "n_genes_by_counts": adata.obs["n_genes_by_counts"].astype(float).tolist(),
            "total_counts": adata.obs["total_counts"].astype(float).tolist(),
            "pct_counts_mt": adata.obs["pct_counts_mt"].astype(float).tolist(),
            "pct_counts_ribo": adata.obs["pct_counts_ribo"].astype(float).tolist(),
        }
    )
    ann.to_csv(outp / "cluster_annotations.csv", index=False)

    um = pd.DataFrame(
        {
            "barcode": adata.obs["barcode"].astype(str).tolist(),
            "sample": adata.obs["sample"].astype(str).tolist(),
            "umap1": umap_xy[:, 0],
            "umap2": umap_xy[:, 1],
            "cluster": labels.astype(int),
            "cell_type": [cell_type_map.get(int(c), f"cluster_{int(c)}") for c in labels],
        }
    )
    um.to_csv(outp / "umap_coords.csv", index=False)

    qc_summary.to_csv(outp / "qc_summary.csv", index=False)

    with open(outp / "cluster_markers_top100_for_llm.json", "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in markers.items()}, f, ensure_ascii=False, indent=2)
    with open(outp / "cluster_markers_top50.json", "w", encoding="utf-8") as f:
        json.dump({str(k): v[:50] for k, v in markers.items()}, f, ensure_ascii=False, indent=2)
    marker_table.to_csv(outp / "cluster_markers_significant.csv", index=False)

    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(8, 6))
        uniq = np.unique(labels)
        for c in uniq:
            m = labels == c
            plt.scatter(umap_xy[m, 0], umap_xy[m, 1], s=6, alpha=0.75, label=f"cluster_{int(c)}")
        plt.xlabel("UMAP1")
        plt.ylabel("UMAP2")
        plt.title("Cell Clusters UMAP (raw clusters)")
        plt.legend(markerscale=2, fontsize=7, loc="best")
        plt.tight_layout()
        plt.savefig(outp / "umap_clusters_unannotated.png", dpi=220)
        plt.close()

        plt.figure(figsize=(8, 6))
        for c in uniq:
            m = labels == c
            name = cell_type_map.get(int(c), f"cluster_{int(c)}")
            plt.scatter(umap_xy[m, 0], umap_xy[m, 1], s=6, alpha=0.75, label=name)
        plt.xlabel("UMAP1")
        plt.ylabel("UMAP2")
        plt.title("Cell Clusters UMAP (annotated)")
        plt.legend(markerscale=2, fontsize=7, loc="best")
        plt.tight_layout()
        plt.savefig(outp / "umap_clusters_annotated.png", dpi=220)
        plt.savefig(outp / "umap_clusters.png", dpi=220)
        plt.close()
    except Exception:
        pass


def annotate_clusters_with_llm(markers: Dict[int, List[str]]) -> Dict[int, str]:
    fallback = {int(k): f"cluster_{k}" for k in markers.keys()}
    try:
        backend = os.environ.get("LLM_BACKEND", "deepseek").lower()
        if backend == "ollama":
            base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
            model = os.environ.get("OLLAMA_MODEL", "deepseek-r1")
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "Return JSON only: {\"labels\": {\"0\":\"...\"}}"},
                    {"role": "user", "content": f"Markers by cluster (top50): {json.dumps(markers)}"},
                ],
                "stream": False,
            }
            import requests

            r = requests.post(f"{base}/api/chat", json=payload, timeout=120)
            r.raise_for_status()
            txt = r.json().get("message", {}).get("content", "")
        else:
            base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
            model = os.environ.get("LLM_MODEL", "deepseek-chat")
            key = os.environ.get("LLM_API_KEY", "")
            headers = {"Content-Type": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a single-cell annotation expert. Return JSON only: {\"labels\": {\"0\":\"cell type\"}}.",
                    },
                    {"role": "user", "content": f"Markers by cluster (top50): {json.dumps(markers)}"},
                ],
                "temperature": 0.0,
            }
            import requests

            r = requests.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=120)
            r.raise_for_status()
            txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        return fallback

    s = txt.find("{")
    e = txt.rfind("}")
    if s == -1 or e == -1:
        return fallback
    try:
        obj = json.loads(txt[s : e + 1])
        labels = obj.get("labels", {}) if isinstance(obj, dict) else {}
        out = {}
        for k in markers.keys():
            out[int(k)] = str(labels.get(str(k), f"cluster_{k}"))
        return out
    except Exception:
        return fallback
