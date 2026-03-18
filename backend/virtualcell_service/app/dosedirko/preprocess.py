from typing import List, Tuple, Optional
import numpy as np
from scipy import sparse


def filter_genes_min_cells(X, gene_names: List[str], min_cells: int):
    if sparse.issparse(X):
        keep = (np.asarray(X.getnnz(axis=0)).ravel() >= min_cells)
    else:
        keep = (np.count_nonzero(X, axis=0) >= min_cells)
    Xf = X[:, keep]
    genes = [g for g, k in zip(gene_names, keep) if k]
    return Xf, genes


def select_top_genes_by_variance(
    X,
    gene_names: List[str],
    n_top: Optional[int],
    include_genes: Optional[List[str]] = None,
):
    if n_top is None or n_top >= X.shape[1]:
        return X, gene_names
    if sparse.issparse(X):
        # variance = E[x^2] - (E[x])^2 for sparse
        mean = np.asarray(X.mean(axis=0)).ravel()
        mean_sq = np.asarray(X.multiply(X).mean(axis=0)).ravel()
        var = mean_sq - mean ** 2
    else:
        var = np.var(X, axis=0)
    idx = np.argsort(var)[::-1][:n_top].tolist()

    if include_genes:
        name_to_idx = {g: i for i, g in enumerate(gene_names)}
        for g in include_genes:
            gi = name_to_idx.get(g)
            if gi is not None and gi not in idx:
                idx.append(gi)

    idx = np.array(idx, dtype=int)
    Xs = X[:, idx]
    genes = [gene_names[i] for i in idx]
    return Xs, genes


def normalize_log1p_cp10k(X):
    """CP10k normalization + log1p. Returns dense float32 matrix."""
    if sparse.issparse(X):
        counts = np.asarray(X.sum(axis=1)).ravel()
        scale = 1e4 / np.maximum(counts, 1.0)
        Xn = sparse.diags(scale) @ X
        Xn = Xn.tocsr(copy=True)
        Xn.data = np.log1p(Xn.data)
        return Xn.toarray().astype(np.float32)
    counts = X.sum(axis=1)
    scale = 1e4 / np.maximum(counts, 1.0)
    Xn = X * scale[:, None]
    Xn = np.log1p(Xn)
    return Xn.astype(np.float32)
