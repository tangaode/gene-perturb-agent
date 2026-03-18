import numpy as np


def apply_dose_ko(W: np.ndarray, g0_idx: int, alpha: float):
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("alpha must be in [0, 1]")
    Wko = W.copy()
    Wko[g0_idx, :] = (1.0 - alpha) * Wko[g0_idx, :]
    return Wko
