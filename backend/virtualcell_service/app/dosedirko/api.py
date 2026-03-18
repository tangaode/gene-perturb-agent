from typing import Optional, Dict
import json
import hashlib
from pathlib import Path
import numpy as np

from .preprocess import filter_genes_min_cells, select_top_genes_by_variance, normalize_log1p_cp10k
from .grn_pcr import build_subsampled_networks
from .tensor_denoise import denoise_cp
from .ko import apply_dose_ko
from .embed_align import build_similarity, spectral_embedding, procrustes_align
from .direction import compute_direct_input, propagate_direction
from .stability import aggregate_runs


def _genes_hash(genes):
    m = hashlib.md5()
    for g in genes:
        m.update(g.encode("utf-8"))
        m.update(b"\n")
    return m.hexdigest()


def _ckpt_paths(ckpt_dir: Path, run_idx: int):
    e_path = ckpt_dir / f"effect_run{run_idx:03d}.npy"
    d_path = ckpt_dir / f"delta_run{run_idx:03d}.npy"
    return e_path, d_path


class DoseDirKO:
    """Dose-aware KO with direction prediction."""

    def __init__(
        self,
        n_subsample: int = 20,
        subsample_frac: float = 0.8,
        pca_k: int = 30,
        ridge_alpha: float = 1.0,
        cp_rank: int = 5,
        embed_dim: int = 20,
        beta: float = 0.2,
        n_hops: int = 3,
        n_runs: int = 30,
        min_cells_frac: float = 0.01,
        n_top_genes: Optional[int] = 3000,
        random_state: int = 0,
    ):
        self.n_subsample = n_subsample
        self.subsample_frac = subsample_frac
        self.pca_k = pca_k
        self.ridge_alpha = ridge_alpha
        self.cp_rank = cp_rank
        self.embed_dim = embed_dim
        self.beta = beta
        self.n_hops = n_hops
        self.n_runs = n_runs
        self.min_cells_frac = min_cells_frac
        self.n_top_genes = n_top_genes
        self.random_state = random_state

    def _run_once(self, Xn: np.ndarray, gene_names, ko_gene: str, alpha: float, seed: int):
        g0_idx = gene_names.index(ko_gene)
        networks = build_subsampled_networks(
            Xn,
            n_subsample=self.n_subsample,
            subsample_frac=self.subsample_frac,
            pca_k=self.pca_k,
            ridge_alpha=self.ridge_alpha,
            random_state=seed,
        )
        _, W_wt = denoise_cp(networks, rank=self.cp_rank)
        W_ko = apply_dose_ko(W_wt, g0_idx, alpha)

        S_wt = build_similarity(W_wt)
        S_ko = build_similarity(W_ko)
        Z_wt = spectral_embedding(S_wt, embed_dim=self.embed_dim)
        Z_ko = spectral_embedding(S_ko, embed_dim=self.embed_dim)
        Z_ko_aligned = procrustes_align(Z_wt, Z_ko)
        effect = np.linalg.norm(Z_wt - Z_ko_aligned, axis=1)

        baseline = Xn.mean(axis=0)
        u = compute_direct_input(W_wt, g0_idx, alpha, baseline)
        delta = propagate_direction(W_wt, u, beta=self.beta, n_hops=self.n_hops)
        return effect.astype(np.float32), delta.astype(np.float32)

    def run(self, X, gene_names, ko_gene: str, alpha: float, checkpoint_dir: Optional[str] = None, resume: bool = True):
        # preprocess
        min_cells = max(1, int(X.shape[0] * self.min_cells_frac))
        Xf, genes = filter_genes_min_cells(X, gene_names, min_cells)
        Xf, genes = select_top_genes_by_variance(
            Xf, genes, self.n_top_genes, include_genes=[ko_gene]
        )
        if ko_gene not in genes:
            raise ValueError(f"ko_gene {ko_gene} not found after filtering")
        Xn = normalize_log1p_cp10k(Xf)

        n_genes = len(genes)
        effects = np.zeros((self.n_runs, n_genes), dtype=np.float32)
        deltas = np.zeros((self.n_runs, n_genes), dtype=np.float32)

        ckpt_dir = None
        if checkpoint_dir:
            ckpt_dir = Path(checkpoint_dir)
            ckpt_dir.mkdir(parents=True, exist_ok=True)
            meta_path = ckpt_dir / "meta.json"
            gene_hash = _genes_hash(genes)
            meta = {
                "ko_gene": ko_gene,
                "alpha": alpha,
                "n_runs": self.n_runs,
                "n_genes": n_genes,
                "genes_hash": gene_hash,
                "params": {
                    "n_subsample": self.n_subsample,
                    "subsample_frac": self.subsample_frac,
                    "pca_k": self.pca_k,
                    "ridge_alpha": self.ridge_alpha,
                    "cp_rank": self.cp_rank,
                    "embed_dim": self.embed_dim,
                    "beta": self.beta,
                    "n_hops": self.n_hops,
                    "min_cells_frac": self.min_cells_frac,
                    "n_top_genes": self.n_top_genes,
                },
            }
            if meta_path.exists():
                old = json.loads(meta_path.read_text(encoding="utf-8"))
                if old.get("genes_hash") != gene_hash or old.get("n_genes") != n_genes:
                    raise ValueError("Checkpoint genes mismatch. Use a new checkpoint_dir.")
            else:
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        for r in range(self.n_runs):
            seed = self.random_state + r * 101
            if ckpt_dir is not None and resume:
                e_path, d_path = _ckpt_paths(ckpt_dir, r)
                if e_path.exists() and d_path.exists():
                    effects[r] = np.load(e_path)
                    deltas[r] = np.load(d_path)
                    continue

            eff, delt = self._run_once(Xn, genes, ko_gene, alpha, seed)
            effects[r] = eff
            deltas[r] = delt

            if ckpt_dir is not None:
                e_path, d_path = _ckpt_paths(ckpt_dir, r)
                np.save(e_path, eff)
                np.save(d_path, delt)

        df = aggregate_runs(effects, deltas, genes)

        df.attrs["ko_gene"] = ko_gene
        df.attrs["alpha"] = alpha
        df.attrs["params"] = {
            "n_subsample": self.n_subsample,
            "subsample_frac": self.subsample_frac,
            "pca_k": self.pca_k,
            "ridge_alpha": self.ridge_alpha,
            "cp_rank": self.cp_rank,
            "embed_dim": self.embed_dim,
            "beta": self.beta,
            "n_hops": self.n_hops,
            "n_runs": self.n_runs,
            "min_cells_frac": self.min_cells_frac,
            "n_top_genes": self.n_top_genes,
        }
        return df

    def run_by_cell_type(self, X, gene_names, cell_types, ko_gene: str, alpha: float):
        """Run per cell type. Returns dict: cell_type -> DataFrame."""
        results: Dict[str, object] = {}
        cell_types = np.asarray(cell_types)
        for ct in np.unique(cell_types):
            idx = np.where(cell_types == ct)[0]
            if idx.size < 10:
                continue
            df = self.run(X[idx], gene_names, ko_gene, alpha)
            df.attrs["cell_type"] = str(ct)
            results[str(ct)] = df
        return results
