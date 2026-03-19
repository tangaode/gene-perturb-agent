import os
import requests

EVIDENCE_URL = os.environ.get("EVIDENCE_URL", "http://evidence_service:8002")
EVIDENCE_TIMEOUT = int(os.environ.get("EVIDENCE_TIMEOUT", "600"))


def verify_batch(input_gene: str, candidates):
    payload = {"input_gene": input_gene, "candidates": candidates}
    resp = requests.post(f"{EVIDENCE_URL}/verify_batch", json=payload, timeout=EVIDENCE_TIMEOUT)
    resp.raise_for_status()
    return resp.json()
