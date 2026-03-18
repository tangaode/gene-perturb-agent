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

    T = np.stack(networks, axis=2)  # genes x genes x n
    Ttl = tl.tensor(T, dtype=tl.float32)
    factors = parafac(Ttl, rank=rank, init="svd", n_iter_max=n_iter_max, verbose=False)
    T_hat = cp_to_tensor(factors)
    T_hat = tl.to_numpy(T_hat)
    W_wt = T_hat.mean(axis=2)
    return T_hat.astype(np.float32), W_wt.astype(np.float32)
