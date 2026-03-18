import os
from typing import List, Set, Dict

import requests
import requests_cache


def _session():
    return requests_cache.CachedSession(
        cache_name=os.environ.get("GPROFILER_CACHE", "gprofiler_cache"),
        expire_after=86400,
    )


def get_leading_genes_multi(
    gene_list: List[str],
    organism: str = "hsapiens",
    sources: List[str] | None = None,
    top_terms: int = 5,
) -> Dict[str, Set[str]]:
    """Return leading genes by source from top g:Profiler terms."""
    if not gene_list:
        return {}
    if sources is None:
        sources = ["GO:BP", "GO:MF", "GO:CC", "REAC", "KEGG", "WP"]
    sess = _session()
    payload = {
        "organism": organism,
        "query": gene_list,
        "sources": sources,
        "user_threshold": 0.05,
    }
    resp = sess.post("https://biit.cs.ut.ee/gprofiler/api/gost/profile", json=payload, timeout=30)
    if resp.status_code != 200:
        return {}
    data = resp.json().get("result", [])
    out: Dict[str, Set[str]] = {s: set() for s in sources}
    for row in data[:top_terms]:
        src = row.get("source")
        if src not in out:
            continue
        for g in row.get("intersection", []) or []:
            out[src].add(str(g))
    return out


def get_leading_genes(gene_list: List[str], organism: str = "hsapiens", top_terms: int = 5) -> Set[str]:
    out = get_leading_genes_multi(gene_list, organism=organism, top_terms=top_terms)
    merged: Set[str] = set()
    for s in out.values():
        merged |= s
    return merged
