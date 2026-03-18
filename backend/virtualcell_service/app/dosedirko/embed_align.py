import numpy as np


def build_similarity(W: np.ndarray):
    A = np.abs(W)
    S = (A + A.T) / 2.0
    np.fill_diagonal(S, 0.0)
    return S.astype(np.float32)


def spectral_embedding(S: np.ndarray, embed_dim: int = 20):
    n = S.shape[0]
    deg = S.sum(axis=1)
    d_inv_sqrt = 1.0 / np.sqrt(deg + 1e-12)
    D_inv = np.diag(d_inv_sqrt)
    L = np.eye(n, dtype=S.dtype) - D_inv @ S @ D_inv
    eigvals, eigvecs = np.linalg.eigh(L)
    idx = np.argsort(eigvals)
    # skip the first eigenvector (smallest eigenvalue)
    start = 1
    end = min(n, start + embed_dim)
    Z = eigvecs[:, idx[start:end]]
    return Z.astype(np.float32)


def procrustes_align(Z_ref: np.ndarray, Z: np.ndarray):
    # Orthogonal Procrustes
    M = Z.T @ Z_ref
    U, _, Vt = np.linalg.svd(M, full_matrices=False)
    R = U @ Vt
    Z_aligned = Z @ R
    return Z_aligned
