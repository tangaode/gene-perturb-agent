import json
import hashlib
import os
from pathlib import Path
from typing import List

import pandas as pd

from .schemas import GeneResult
from .dosedirko.io import read_10x_mtx
from .dosedirko.api import DoseDirKO


DATA_DIR = Path(os.environ.get("MTX_DIR", "/data/mtx"))
CACHE_DIR = Path(os.environ.get("VCACHE_DIR", "/data/cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USE_SAMPLE = os.environ.get("VC_USE_SAMPLE", "0") == "1"
RETURN_TOPN = int(os.environ.get("VC_RETURN_TOPN", "500"))

_DATA = None  # (X, genes)


def _load_data():
    global _DATA
    if _DATA is None:
        X, genes, barcodes = read_10x_mtx(str(DATA_DIR))
        _DATA = (X, genes, barcodes)
    return _DATA


def _apply_cell_group_filter(X, barcodes):
    group = os.environ.get("VC_CELL_GROUP", "").strip()
    ann_file = os.environ.get("VC_CLUSTER_META", "").strip()
    if not group or not ann_file:
        return X
    p = Path(ann_file)
    if not p.exists():
        return X
    try:
        ann = pd.read_csv(p)
    except Exception:
        return X
    if "barcode" not in ann.columns or "cluster" not in ann.columns:
        return X
    ann["barcode"] = ann["barcode"].astype(str)
    bar_idx = {str(b): i for i, b in enumerate(barcodes)}
    group_l = group.lower()
    if group_l.startswith("cluster:"):
        val = group.split(":", 1)[1]
        sel = ann[ann["cluster"].astype(str) == str(val)]
    elif group_l.startswith("cell_type:") and "cell_type" in ann.columns:
        val = group.split(":", 1)[1].strip().lower()
        sel = ann[ann["cell_type"].astype(str).str.lower() == val]
    else:
        # tolerant match: cluster id first, then cell_type exact if present.
        sel = ann[ann["cluster"].astype(str) == group]
        if sel.empty and "cell_type" in ann.columns:
            sel = ann[ann["cell_type"].astype(str).str.lower() == group_l]
    idx = [bar_idx[b] for b in sel["barcode"].tolist() if b in bar_idx]
    if len(idx) < 20:
        return X
    return X[idx]


def _model_params():
    return {
        "n_subsample": int(os.environ.get("VC_N_SUBSAMPLE", "15")),
        "subsample_frac": float(os.environ.get("VC_SUBSAMPLE_FRAC", "0.8")),
        "pca_k": int(os.environ.get("VC_PCA_K", "30")),
        "ridge_alpha": float(os.environ.get("VC_RIDGE_ALPHA", "1.0")),
        "cp_rank": int(os.environ.get("VC_CP_RANK", "5")),
        "embed_dim": int(os.environ.get("VC_EMBED_DIM", "20")),
        "beta": float(os.environ.get("VC_BETA", "0.2")),
        "n_hops": int(os.environ.get("VC_N_HOPS", "3")),
        "n_runs": int(os.environ.get("VC_N_RUNS", "20")),
        "min_cells_frac": float(os.environ.get("VC_MIN_CELLS_FRAC", "0.01")),
        "n_top_genes": int(os.environ.get("VC_N_TOP_GENES", "2500")),
        "random_state": int(os.environ.get("VC_RANDOM_STATE", "42")),
    }


def _cache_path(gene: str, alpha: float, context: str, params: dict):
    safe_gene = gene.replace("/", "_")
    safe_ctx = context.replace("/", "_")
    sig = _params_signature(params)
    return CACHE_DIR / f"{safe_gene}_a{alpha:.2f}_{safe_ctx}_{sig}.csv"


def _params_signature(params: dict) -> str:
    items = sorted((str(k), str(v)) for k, v in params.items())
    raw = "|".join([f"{k}={v}" for k, v in items])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]


def _ckpt_dir(gene: str, alpha: float, context: str, params: dict) -> Path:
    safe_gene = gene.replace("/", "_")
    safe_ctx = context.replace("/", "_")
    sig = _params_signature(params)
    return CACHE_DIR / f"ckpt_{safe_gene}_{alpha:.2f}_{safe_ctx}_{sig}"


def _df_to_results(df: pd.DataFrame) -> List[GeneResult]:
    if RETURN_TOPN > 0:
        df = df.head(RETURN_TOPN)
    results = []
    for _, row in df.iterrows():
        direction = str(row.get("direction", ""))
        p_up = float(row.get("p_up", 0.0))
        p_down = float(row.get("p_down", 0.0))
        if direction not in ("up", "down"):
            direction = "up" if p_up >= p_down else "down"
        results.append(GeneResult(
            gene=str(row["gene"]),
            effect_score=float(row["effect_mean"]),
            delta_sign=direction,
            p_up=p_up,
            p_down=p_down,
        ))
    return results


def run_virtualcell(gene: str, alpha: float, context: str = "default") -> List[GeneResult]:
    """Run DoseDirKO (cached) and return gene-level results.

    If VC_USE_SAMPLE=1, load sample output instead.
    """
    if USE_SAMPLE:
        data_path = Path(__file__).parent / "sample_virtualcell_output.json"
        raw = json.loads(data_path.read_text(encoding="utf-8"))
        return [GeneResult(**r) for r in raw]

    gene = gene.strip().upper()
    params = _model_params()
    cache = _cache_path(gene, alpha, context, params)
    if cache.exists():
        df = pd.read_csv(cache)
        return _df_to_results(df)

    X, genes, barcodes = _load_data()
    X = _apply_cell_group_filter(X, barcodes)
    model = DoseDirKO(**params)
    ckpt = _ckpt_dir(gene, alpha, context, params)
    df = model.run(X, genes, ko_gene=gene, alpha=alpha, checkpoint_dir=str(ckpt))
    df.to_csv(cache, index=False)
    return _df_to_results(df)
