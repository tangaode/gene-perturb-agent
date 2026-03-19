import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans


def _normalize_log1p(X: sparse.csr_matrix, scale: float = 1e4) -> sparse.csr_matrix:
    lib = np.asarray(X.sum(axis=1)).ravel().astype(np.float64)
    lib[lib <= 0] = 1.0
    factors = scale / lib
    Xn = X.multiply(factors[:, None]).tocsr()
    Xn.data = np.log1p(Xn.data)
    return Xn


def _select_genes_by_mean(X: sparse.csr_matrix, genes: List[str], n_top: int = 2000) -> Tuple[sparse.csr_matrix, List[str], np.ndarray]:
    means = np.asarray(X.mean(axis=0)).ravel()
    n = min(n_top, X.shape[1])
    idx = np.argsort(-means)[:n]
    idx = np.sort(idx)
    return X[:, idx].tocsr(), [genes[i] for i in idx], idx


def cluster_cells(
    X: sparse.csr_matrix,
    genes: List[str],
    barcodes: List[str],
    n_pcs: int = 30,
    n_clusters: int = 8,
    n_top_genes: int = 2000,
    random_state: int = 42,
):
    Xn = _normalize_log1p(X)
    Xsel, gsel, sel_idx = _select_genes_by_mean(Xn, genes, n_top=n_top_genes)

    n_comp = max(2, min(n_pcs, Xsel.shape[1] - 1, Xsel.shape[0] - 1))
    svd = TruncatedSVD(n_components=n_comp, random_state=random_state)
    pcs = svd.fit_transform(Xsel)

    k = max(2, min(n_clusters, X.shape[0] // 30 if X.shape[0] >= 60 else 2))
    km = KMeans(n_clusters=k, random_state=random_state, n_init=20)
    labels = km.fit_predict(pcs)

    return labels, pcs, Xn


def compute_top_markers(Xn: sparse.csr_matrix, genes: List[str], labels: np.ndarray, top_n: int = 50) -> Dict[int, List[str]]:
    out: Dict[int, List[str]] = {}
    uniq = np.unique(labels)
    for c in uniq:
        in_mask = labels == c
        out_mask = ~in_mask
        if in_mask.sum() == 0 or out_mask.sum() == 0:
            out[int(c)] = []
            continue
        mu_in = np.asarray(Xn[in_mask].mean(axis=0)).ravel()
        mu_out = np.asarray(Xn[out_mask].mean(axis=0)).ravel()
        score = np.log2((mu_in + 1e-6) / (mu_out + 1e-6))
        idx = np.argsort(-score)[:top_n]
        out[int(c)] = [genes[i] for i in idx if score[i] > 0]
    return out


def run_umap(pcs: np.ndarray, random_state: int = 42):
    try:
        import umap
    except Exception as e:
        raise ImportError("umap-learn is required for UMAP export") from e
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.3, random_state=random_state)
    emb = reducer.fit_transform(pcs)
    return emb


def save_outputs(
    out_dir: str,
    barcodes: List[str],
    labels: np.ndarray,
    umap_xy: np.ndarray,
    markers: Dict[int, List[str]],
    cell_type_map: Dict[int, str],
):
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)

    ann = pd.DataFrame({
        "barcode": barcodes,
        "cluster": labels.astype(int),
        "cell_type": [cell_type_map.get(int(c), f"cluster_{int(c)}") for c in labels],
    })
    ann.to_csv(outp / "cluster_annotations.csv", index=False)

    um = pd.DataFrame({
        "barcode": barcodes,
        "umap1": umap_xy[:, 0],
        "umap2": umap_xy[:, 1],
        "cluster": labels.astype(int),
        "cell_type": [cell_type_map.get(int(c), f"cluster_{int(c)}") for c in labels],
    })
    um.to_csv(outp / "umap_coords.csv", index=False)

    with open(outp / "cluster_markers_top50.json", "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in markers.items()}, f, ensure_ascii=False, indent=2)

    # UMAP plot
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 6))
        uniq = np.unique(labels)
        for c in uniq:
            m = labels == c
            name = cell_type_map.get(int(c), f"cluster_{int(c)}")
            plt.scatter(umap_xy[m, 0], umap_xy[m, 1], s=6, alpha=0.75, label=f"{name}")
        plt.xlabel("UMAP1")
        plt.ylabel("UMAP2")
        plt.title("Cell Clusters UMAP")
        plt.legend(markerscale=2, fontsize=7, loc="best")
        plt.tight_layout()
        plt.savefig(outp / "umap_clusters.png", dpi=220)
        plt.close()
    except Exception:
        pass


def annotate_clusters_with_llm(markers: Dict[int, List[str]]) -> Dict[int, str]:
    backend = os.environ.get("LLM_BACKEND", "relay").lower()
    if backend == "ollama":
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        model = os.environ.get("OLLAMA_MODEL", "deepseek-r1")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Return JSON only: {\"labels\": {\"0\":\"...\"}}"},
                {"role": "user", "content": f"Markers by cluster (top50): {json.dumps(markers)}"},
            ],
            "stream": False,
        }
        import requests
        r = requests.post(f"{base}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        txt = r.json().get("message", {}).get("content", "")
    else:
        base = os.environ.get("LLM_BASE_URL", "http://123.207.10.233:8010/v1").rstrip("/")
        model = os.environ.get("LLM_MODEL", "deepseek-chat")
        key = os.environ.get("LLM_API_KEY", "")
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a single-cell annotation expert. Return JSON only: {\"labels\": {\"0\":\"cell type\"}}."},
                {"role": "user", "content": f"Markers by cluster (top50): {json.dumps(markers)}"},
            ],
            "temperature": 0.0,
        }
        import requests
        r = requests.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=120)
        r.raise_for_status()
        txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    s = txt.find("{")
    e = txt.rfind("}")
    if s == -1 or e == -1:
        return {int(k): f"cluster_{k}" for k in markers.keys()}
    try:
        obj = json.loads(txt[s : e + 1])
        labels = obj.get("labels", {}) if isinstance(obj, dict) else {}
        out = {}
        for k in markers.keys():
            out[int(k)] = str(labels.get(str(k), f"cluster_{k}"))
        return out
    except Exception:
        return {int(k): f"cluster_{k}" for k in markers.keys()}
