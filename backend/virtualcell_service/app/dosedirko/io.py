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


def _is_10x_dir(base: Path) -> bool:
    has_matrix = (base / "matrix.mtx").exists() or (base / "matrix.mtx.gz").exists()
    has_features = (
        (base / "features.tsv").exists()
        or (base / "features.tsv.gz").exists()
        or (base / "genes.tsv").exists()
        or (base / "genes.tsv.gz").exists()
    )
    has_barcodes = (base / "barcodes.tsv").exists() or (base / "barcodes.tsv.gz").exists()
    return has_matrix and has_features and has_barcodes


def _find_10x_dirs(base: Path) -> List[Path]:
    if _is_10x_dir(base):
        return [base]
    dirs = []
    for p in base.rglob("*"):
        if p.is_dir() and _is_10x_dir(p):
            dirs.append(p)
    return sorted(dirs)


def _read_single_10x(base: Path) -> Tuple[sparse.csr_matrix, List[str], List[str], str]:
    mtx_path = _pick_existing(base, ["matrix.mtx.gz", "matrix.mtx"])
    feat_path = _pick_existing(base, ["features.tsv.gz", "features.tsv", "genes.tsv.gz", "genes.tsv"])
    bc_path = _pick_existing(base, ["barcodes.tsv.gz", "barcodes.tsv"])

    mtx = mmread(_open_binary(mtx_path)).tocsr()
    X = mtx.T.tocsr()

    with _open_text(feat_path) as f:
        genes = []
        for line in f:
            cols = line.strip().split("\t")
            genes.append(cols[1] if len(cols) > 1 else cols[0])
    with _open_text(bc_path) as f:
        barcodes = [line.strip() for line in f]

    genes = _make_unique(genes)
    sample_name = base.name
    return X, genes, barcodes, sample_name


def _align_to_union(X: sparse.csr_matrix, genes: List[str], union_map: dict, n_union: int) -> sparse.csr_matrix:
    xcoo = X.tocoo()
    mapped_cols = np.fromiter((union_map[genes[c]] for c in xcoo.col), dtype=np.int64, count=xcoo.col.shape[0])
    return sparse.coo_matrix((xcoo.data, (xcoo.row, mapped_cols)), shape=(X.shape[0], n_union)).tocsr()


def read_10x_mtx(dir_path: str) -> Tuple[sparse.csr_matrix, List[str], List[str]]:
    """Read one or more 10x MTX folders (gz or plain text variants).

    Returns X (cells x genes) CSR, gene_names, cell_barcodes.
    """
    base = Path(dir_path)
    sample_dirs = _find_10x_dirs(base)
    if not sample_dirs:
        raise FileNotFoundError(
            f"No valid 10x MTX folder found in {base}. Expected matrix/features(or genes)/barcodes files."
        )

    parts = [_read_single_10x(d) for d in sample_dirs]
    if len(parts) == 1:
        X, genes, barcodes, _ = parts[0]
        return X, genes, barcodes

    union_genes = []
    union_map = {}
    for _, genes, _, _ in parts:
        for g in genes:
            if g not in union_map:
                union_map[g] = len(union_genes)
                union_genes.append(g)

    aligned = []
    merged_barcodes = []
    for X, genes, barcodes, sample_name in parts:
        Xa = _align_to_union(X, genes, union_map, len(union_genes))
        aligned.append(Xa)
        merged_barcodes.extend([f"{sample_name}:{b}" for b in barcodes])

    Xall = sparse.vstack(aligned, format="csr")
    return Xall, union_genes, merged_barcodes


def load_anndata(adata, cell_type_key: Optional[str] = None):
    """Extract X, gene_names, optional cell_type labels from AnnData."""
    X = adata.X
    gene_names = [str(x) for x in adata.var_names]
    cell_types = None
    if cell_type_key is not None and cell_type_key in adata.obs:
        cell_types = adata.obs[cell_type_key].astype(str).to_numpy()
    return X, gene_names, cell_types
