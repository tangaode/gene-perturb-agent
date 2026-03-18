import os
from pathlib import Path
from typing import Tuple, List, Dict, Set

_CORUM_INDEX = None


def _load_corum():
    global _CORUM_INDEX
    if _CORUM_INDEX is not None:
        return _CORUM_INDEX
    path = os.environ.get("CORUM_FILE")
    if not path:
        _CORUM_INDEX = {}
        return _CORUM_INDEX
    p = Path(path)
    if not p.exists():
        _CORUM_INDEX = {}
        return _CORUM_INDEX
    gene_to_complex: dict[str, set[str]] = {}
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            complex_id = parts[0]
            subunits = parts[-1]
            for g in subunits.split(";"):
                gg = g.strip()
                if not gg:
                    continue
                gene_to_complex.setdefault(gg, set()).add(complex_id)
    _CORUM_INDEX = gene_to_complex
    return _CORUM_INDEX


def corum_shared_complex_score(gene_a: str, gene_b: str) -> Tuple[float, List[Dict]]:
    index = _load_corum()
    if not index:
        return 0.0, []
    ca = index.get(gene_a, set())
    cb = index.get(gene_b, set())
    shared = ca.intersection(cb)
    if not shared:
        return 0.0, []
    score = min(1.0, 0.2 + 0.05 * len(shared))
    items = [{
        "source": "corum",
        "text": "shared complex membership",
        "meta": {"shared_complexes": list(shared)[:3]},
    }]
    return score, items
