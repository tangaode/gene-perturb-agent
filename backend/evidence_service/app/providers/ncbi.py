import os
import re
from typing import List, Dict, Tuple

import requests
import requests_cache


_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _session():
    api_key = os.environ.get("NCBI_API_KEY") or None
    email = os.environ.get("NCBI_EMAIL") or None
    sess = requests_cache.CachedSession(
        cache_name=os.environ.get("NCBI_CACHE", "ncbi_cache"),
        expire_after=86400,
    )
    sess.params = {"tool": "gene-perturb-agent"}
    if api_key:
        sess.params["api_key"] = api_key
    if email:
        sess.params["email"] = email
    return sess


def get_gene_summary(gene: str, organism: str = "Homo sapiens") -> str:
    """Fetch Gene summary from NCBI Gene database. Best-effort."""
    sess = _session()
    term = f"{gene}[Gene Name] AND {organism}[Organism]"
    r = sess.get(f"{_BASE}/esearch.fcgi", params={"db": "gene", "term": term, "retmode": "json"}, timeout=20)
    r.raise_for_status()
    data = r.json()
    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return ""
    gene_id = ids[0]
    s = sess.get(f"{_BASE}/esummary.fcgi", params={"db": "gene", "id": gene_id, "retmode": "json"}, timeout=20)
    s.raise_for_status()
    summary = s.json().get("result", {}).get(gene_id, {}).get("summary", "")
    return summary or ""


def pubmed_cooccur(gene_a: str, gene_b: str, retmax: int = 3) -> List[Dict]:
    """Search PubMed for co-occurrence of gene_a and gene_b in title/abstract."""
    sess = _session()
    term = f"{gene_a}[Title/Abstract] AND {gene_b}[Title/Abstract]"
    r = sess.get(f"{_BASE}/esearch.fcgi", params={"db": "pubmed", "term": term, "retmax": retmax, "retmode": "json"}, timeout=20)
    r.raise_for_status()
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    ids_str = ",".join(ids)
    f = sess.get(f"{_BASE}/efetch.fcgi", params={"db": "pubmed", "id": ids_str, "retmode": "xml"}, timeout=20)
    f.raise_for_status()

    # light XML parse
    import xml.etree.ElementTree as ET
    root = ET.fromstring(f.text)
    items = []
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID") or ""
        title = art.findtext(".//ArticleTitle") or ""
        abs_nodes = art.findall(".//AbstractText")
        abstract = " ".join([n.text or "" for n in abs_nodes]).strip()
        items.append({"pmid": pmid, "title": title, "abstract": abstract})
    return items


def score_direction(text: str, direction: str) -> float:
    if not text:
        return 0.0
    t = text.lower()
    up_terms = ["upregulate", "upregulated", "activate", "activation", "increase", "induces"]
    down_terms = ["downregulate", "downregulated", "inhibit", "inhibition", "decrease", "suppresses"]
    if direction == "up":
        return 0.3 if any(k in t for k in up_terms) else 0.0
    return 0.3 if any(k in t for k in down_terms) else 0.0


def evidence_from_ncbi(input_gene: str, candidate_gene: str, direction: str) -> Tuple[float, float, List[Dict]]:
    summary = get_gene_summary(candidate_gene)
    co = pubmed_cooccur(input_gene, candidate_gene, retmax=3)

    evidence_rel = 0.0
    if summary:
        evidence_rel += 0.2
    if co:
        evidence_rel += 0.3 + min(0.5, 0.1 * len(co))
    evidence_rel = min(1.0, evidence_rel)

    text_blob = summary + "\n" + "\n".join([c.get("title", "") + " " + c.get("abstract", "") for c in co])
    evidence_dir = min(0.3, score_direction(text_blob, direction))

    items = []
    if summary:
        items.append({"source": "ncbi_gene", "text": summary[:300], "meta": {"gene": candidate_gene}})
    for c in co[:2]:
        items.append({"source": "pubmed", "text": (c.get("title", "") + " " + c.get("abstract", ""))[:300], "meta": {"pmid": c.get("pmid", "")}})

    return evidence_rel, evidence_dir, items
