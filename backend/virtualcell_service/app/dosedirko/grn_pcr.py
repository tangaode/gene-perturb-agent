from typing import List
import numpy as np
from sklearn.decomposition import PCA


def build_pcr_network(X: np.ndarray, pca_k: int = 30, ridge_alpha: float = 1.0, random_state: int = 0):
    """Build gene regulatory network using PCR + ridge.

    X: cells x genes (dense)
    Returns W: genes x genes (dense)
    """
    n_cells, n_genes = X.shape
    # Center genes
    mean = X.mean(axis=0, keepdims=True)
    Xc = X - mean

    k = min(pca_k, min(n_cells - 1, n_genes - 1))
    if k < 2:
        raise ValueError("pca_k too small for data size")

    pca = PCA(n_components=k, svd_solver="randomized", random_state=random_state)
    T = pca.fit_transform(Xc)  # cells x k
    P = pca.components_.T       # genes x k

    # Ridge regression: B = (T^T T + alpha I)^-1 T^T Xc
    TT = T.T @ T
    A = TT + ridge_alpha * np.eye(k, dtype=T.dtype)
    # Solve for all genes at once
    B = np.linalg.solve(A, T.T @ Xc)  # k x genes

    W = P @ B  # genes x genes
    # zero self edges
    np.fill_diagonal(W, 0.0)
    return W.astype(np.float32)


def build_subsampled_networks(
    X: np.ndarray,
    n_subsample: int = 20,
    subsample_frac: float = 0.8,
    pca_k: int = 30,
    ridge_alpha: float = 1.0,
    random_state: int = 0,
) -> List[np.ndarray]:
    rng = np.random.default_rng(random_state)
    n_cells = X.shape[0]
    m = max(2, int(n_cells * subsample_frac))
    nets = []
    for i in range(n_subsample):
        idx = rng.choice(n_cells, size=m, replace=False)
        Xi = X[idx]
        Wi = build_pcr_network(Xi, pca_k=pca_k, ridge_alpha=ridge_alpha, random_state=random_state + i + 1)
        nets.append(Wi)
    return nets
