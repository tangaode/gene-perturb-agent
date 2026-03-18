import os
from typing import Tuple, List, Dict

import requests
import requests_cache


def _session():
    return requests_cache.CachedSession(
        cache_name=os.environ.get("STRING_CACHE", "string_cache"),
        expire_after=86400,
    )


def string_ppi_score(gene_a: str, gene_b: str, species: int = 9606) -> Tuple[float, List[Dict]]:
    """Return PPI evidence score from STRING (0-1) and evidence items."""
    sess = _session()
    identifiers = f"{gene_a}%0D{gene_b}"
    url = "https://string-db.org/api/json/network"
    resp = sess.get(url, params={"identifiers": identifiers, "species": species}, timeout=20)
    if resp.status_code != 200:
        return 0.0, []
    data = resp.json()
    if not data:
        return 0.0, []
    # combined_score is 0..1000
    max_score = max([d.get("combined_score", 0) for d in data])
    score = min(1.0, float(max_score) / 1000.0)
    items = []
    for d in data[:2]:
        items.append({
            "source": "string",
            "text": f"{d.get('preferredName_A')} - {d.get('preferredName_B')} (score {d.get('combined_score')})",
            "meta": {"score": d.get("combined_score")},
        })
    return score, items
