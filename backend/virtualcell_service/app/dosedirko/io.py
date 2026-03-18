import gzip
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
from scipy.io import mmread
from scipy import sparse


def _make_unique(names: List[str]) -> List[str]:
    seen = {}
    out = []
    for n in names:
        if n not in seen:
            seen[n] = 0
            out.append(n)
        else:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
    return out


def _pick_existing(base: Path, candidates: List[str]) -> Path:
    for name in candidates:
        p = base / name
        if p.exists():
            return p
    joined = ", ".join(candidates)
    raise FileNotFoundError(f"None of expected files found in {base}: {joined}")


def _open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open("rt", encoding="utf-8")


def _open_binary(path: Path):
    return gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb")


def read_10x_mtx(dir_path: str) -> Tuple[sparse.csr_matrix, List[str], List[str]]:
    """Read 10x MTX (gz or plain text variants).

    Returns X (cells x genes) CSR, gene_names, cell_barcodes.
    """
    base = Path(dir_path)
    mtx_path = _pick_existing(base, ["matrix.mtx.gz", "matrix.mtx"])
    feat_path = _pick_existing(base, ["features.tsv.gz", "features.tsv", "genes.tsv.gz", "genes.tsv"])
    bc_path = _pick_existing(base, ["barcodes.tsv.gz", "barcodes.tsv"])

    mtx = mmread(_open_binary(mtx_path)).tocsr()
    # 10x is genes x cells -> transpose to cells x genes
    X = mtx.T.tocsr()

    with _open_text(feat_path) as f:
        genes = []
        for line in f:
            cols = line.strip().split("\t")
            genes.append(cols[1] if len(cols) > 1 else cols[0])
    with _open_text(bc_path) as f:
        barcodes = [line.strip() for line in f]

    genes = _make_unique(genes)
    return X, genes, barcodes


def load_anndata(adata, cell_type_key: Optional[str] = None):
    """Extract X, gene_names, optional cell_type labels from AnnData."""
    X = adata.X
    gene_names = [str(x) for x in adata.var_names]
    cell_types = None
    if cell_type_key is not None and cell_type_key in adata.obs:
        cell_types = adata.obs[cell_type_key].astype(str).to_numpy()
    return X, gene_names, cell_types
