import os
from typing import List, Set, Dict

import requests
import requests_cache


def _session():
    return requests_cache.CachedSession(
        cache_name=os.environ.get("ENRICHR_CACHE", "enrichr_cache"),
        expire_after=86400,
    )


def _add_list(sess, gene_list: List[str]) -> int | None:
    add_resp = sess.post(
        "https://maayanlab.cloud/Enrichr/addList",
        data={"list": "\n".join(gene_list), "description": "gene-perturb-agent"},
        timeout=20,
    )
    if add_resp.status_code != 200:
        return None
    return add_resp.json().get("userListId")


def get_leading_genes_multi(
    gene_list: List[str],
    libraries: List[str],
    top_terms: int = 5,
) -> Dict[str, Set[str]]:
    """Return leading genes for multiple Enrichr libraries."""
    if not gene_list:
        return {lib: set() for lib in libraries}
    sess = _session()
    user_list_id = _add_list(sess, gene_list)
    if not user_list_id:
        return {lib: set() for lib in libraries}

    out: Dict[str, Set[str]] = {}
    for library in libraries:
        enrich_resp = sess.get(
            "https://maayanlab.cloud/Enrichr/enrich",
            params={"userListId": user_list_id, "backgroundType": library},
            timeout=20,
        )
        if enrich_resp.status_code != 200:
            out[library] = set()
            continue
        data = enrich_resp.json().get(library, [])
        leading = set()
        for row in data[:top_terms]:
            # row format: [rank, term_name, pval, z, combined, genes, ...]
            if len(row) >= 6 and isinstance(row[5], str):
                for g in row[5].split(";"):
                    leading.add(g.strip())
        out[library] = leading
    return out


def get_leading_genes(gene_list: List[str], library: str = "KEGG_2021_Human", top_terms: int = 5) -> Set[str]:
    return get_leading_genes_multi(gene_list, [library], top_terms=top_terms).get(library, set())
