import numpy as np


def compute_direct_input(W: np.ndarray, g0_idx: int, alpha: float, baseline: np.ndarray):
    """Direct perturbation input u."""
    a0 = baseline[g0_idx]
    u = -alpha * W[g0_idx, :] * a0
    return u.astype(np.float32)


def propagate_direction(W: np.ndarray, u: np.ndarray, beta: float = 0.2, n_hops: int = 3):
    """Signed propagation on directed network."""
    delta = u.astype(np.float32).copy()
    cur = u
    for i in range(n_hops):
        cur = W.T @ cur
        delta += (beta ** (i + 1)) * cur
    return delta.astype(np.float32)
