from typing import Dict
import numpy as np
import pandas as pd


def aggregate_runs(effect_scores: np.ndarray, deltas: np.ndarray, gene_names, top_k: int = 50):
    """Aggregate across runs.

    effect_scores: (n_runs, n_genes)
    deltas: (n_runs, n_genes)
    """
    n_runs, n_genes = effect_scores.shape
    effect_mean = effect_scores.mean(axis=0)
    ci_low = np.quantile(effect_scores, 0.025, axis=0)
    ci_high = np.quantile(effect_scores, 0.975, axis=0)

    delta_mean = deltas.mean(axis=0)
    p_up = (deltas > 0).mean(axis=0)
    p_down = (deltas < 0).mean(axis=0)

    direction = np.full(n_genes, "ambiguous", dtype=object)
    direction[p_up >= 0.8] = "up"
    direction[p_down >= 0.8] = "down"

    # Top-K frequency by effect_score
    top_freq = np.zeros(n_genes, dtype=np.float32)
    for r in range(n_runs):
        idx = np.argsort(effect_scores[r])[::-1][:top_k]
        top_freq[idx] += 1
    top_freq = top_freq / n_runs

    df = pd.DataFrame({
        "gene": gene_names,
        "effect_mean": effect_mean,
        "effect_ci_low": ci_low,
        "effect_ci_high": ci_high,
        "delta_mean": delta_mean,
        "direction": direction,
        "p_up": p_up,
        "p_down": p_down,
        "topk_freq": top_freq,
    })
    df = df.sort_values("effect_mean", ascending=False).reset_index(drop=True)
    return df
