import os
from typing import Tuple, List, Dict

import requests
import requests_cache


def _session():
    return requests_cache.CachedSession(
        cache_name=os.environ.get("BIOGRID_CACHE", "biogrid_cache"),
        expire_after=86400,
    )


def biogrid_ppi_score(gene_a: str, gene_b: str) -> Tuple[float, List[Dict]]:
    """Query BioGRID interactions (requires BIOGRID_API_KEY)."""
    key = os.environ.get("BIOGRID_API_KEY")
    if not key:
        return 0.0, []
    sess = _session()
    url = "https://webservice.thebiogrid.org/interactions/"
    params = {
        "searchNames": "true",
        "geneList": f"{gene_a}|{gene_b}",
        "includeInteractors": "false",
        "format": "json",
        "accesskey": key,
    }
    resp = sess.get(url, params=params, timeout=20)
    if resp.status_code != 200:
        return 0.0, []
    data = resp.json()
    n = len(data) if isinstance(data, dict) else 0
    if n == 0:
        return 0.0, []
    score = min(1.0, 0.2 * n)
    items = []
    for k, v in list(data.items())[:2]:
        items.append({
            "source": "biogrid",
            "text": f"{v.get('OFFICIAL_SYMBOL_A')} - {v.get('OFFICIAL_SYMBOL_B')}",
            "meta": {"biogrid_id": v.get("BIOGRID_INTERACTION_ID")},
        })
    return score, items
