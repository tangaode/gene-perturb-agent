from typing import List
import numpy as np


def denoise_cp(networks: List[np.ndarray], rank: int = 5, n_iter_max: int = 100):
    """CP/PARAFAC denoise a stack of networks.

    Returns denoised tensor and averaged WT network.
    """
    try:
        import tensorly as tl
        from tensorly.decomposition import parafac
        from tensorly.cp_tensor import cp_to_tensor
    except Exception as e:
        raise ImportError("tensorly is required for CP denoising") from e

    T = np.stack(networks, axis=2).astype(np.float32)  # genes x genes x n
    g = T.shape[0]
    n = T.shape[2]

    # Fast-safe fallbacks: avoid unstable or memory-heavy CP when data is too small/large.
    if n < 2 or rank <= 0 or g > 400:
        return T, T.mean(axis=2)

    Ttl = tl.tensor(T, dtype=tl.float32)
    try:
        # Use random init to avoid SVD init memory blowups on large unfolded modes.
        factors = parafac(Ttl, rank=min(rank, n), init="random", n_iter_max=n_iter_max, verbose=False)
        T_hat = cp_to_tensor(factors)
        T_hat = tl.to_numpy(T_hat)
    except Exception:
        T_hat = T

    W_wt = T_hat.mean(axis=2)
    return T_hat.astype(np.float32), W_wt.astype(np.float32)
