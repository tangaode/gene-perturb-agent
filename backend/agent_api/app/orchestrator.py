import json
import os
from typing import Dict, List
import requests

from .candidate_filter import filter_candidates
from .llm_ollama import chat
from .prompts import system_prompt_json, prompt_generation, prompt_modify, prompt_summarize
from .evidence_client import verify_batch
from .ranker import rank_candidates

VIRTUALCELL_URL = os.environ.get("VIRTUALCELL_URL", "http://virtualcell_service:8001")
VERIFY_TOPK = int(os.environ.get("VERIFY_TOPK", "10"))
VIRTUALCELL_TIMEOUT = int(os.environ.get("VIRTUALCELL_TIMEOUT", "36000"))


def _call_virtualcell(gene: str, alpha: float, context: str):
    resp = requests.post(
        f"{VIRTUALCELL_URL}/perturb",
        json={"gene": gene, "alpha": alpha, "context": context},
        timeout=VIRTUALCELL_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_json(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


def _llm_call(payload: str):
    messages = [
        {"role": "system", "content": system_prompt_json()},
        {"role": "user", "content": payload},
    ]
    text = chat(messages)
    return _parse_json(text)


def _build_llm_rank(items: List[Dict]) -> Dict[str, float]:
    rank = {}
    for i, it in enumerate(items):
        gene = it.get("gene")
        if not gene:
            continue
        # higher rank -> higher score
        rank[gene] = 1.0 - (i / max(len(items), 1))
    return rank


def run_pipeline(gene: str, alpha: float, context: str) -> Dict:
    log = {}
    vcell = _call_virtualcell(gene, alpha, context)
    results = vcell.get("results", [])

    up, down = filter_candidates(results)
    log["up_candidates"] = len(up)
    log["down_candidates"] = len(down)

    up_pool = [{"gene": r["gene"], "effect_score": r["effect_score"], "p_up": r["p_up"]} for r in up]
    down_pool = [{"gene": r["gene"], "effect_score": r["effect_score"], "p_down": r["p_down"]} for r in down]

    # Call #1: generation (LLM selects top10 + claims)
    llm_gen = None
    try:
        llm_gen = _llm_call(prompt_generation(gene, up_pool, down_pool))
        log["llm_generation"] = "ok" if llm_gen else "invalid"
    except Exception:
        log["llm_generation"] = "failed"

    if llm_gen and llm_gen.get("top_up") and llm_gen.get("top_down"):
        up_top = llm_gen["top_up"][:VERIFY_TOPK]
        down_top = llm_gen["top_down"][:VERIFY_TOPK]
    else:
        up_top = up_pool[:VERIFY_TOPK]
        down_top = down_pool[:VERIFY_TOPK]

    # evidence verify
    reports = []
    try:
        verify_candidates = [
            {"gene": r["gene"], "direction": "up"} for r in up_top
        ] + [
            {"gene": r["gene"], "direction": "down"} for r in down_top
        ]
        evidence = verify_batch(gene, verify_candidates)
        reports = evidence.get("reports", [])
        log["evidence"] = "ok"
    except Exception:
        log["evidence"] = "failed"

    # Call #3: modification (LLM revises list with evidence)
    llm_mod = None
    try:
        llm_mod = _llm_call(prompt_modify(gene, llm_gen or {}, reports))
        log["llm_modification"] = "ok" if llm_mod else "invalid"
    except Exception:
        log["llm_modification"] = "failed"

    if llm_mod and llm_mod.get("top_up") and llm_mod.get("top_down"):
        up_top = llm_mod["top_up"][:VERIFY_TOPK]
        down_top = llm_mod["top_down"][:VERIFY_TOPK]

    llm_rank_up = _build_llm_rank(up_top) if up_top else {}
    llm_rank_down = _build_llm_rank(down_top) if down_top else {}

    ranked_up = rank_candidates(up_top, reports, "up", llm_rank=llm_rank_up)
    ranked_down = rank_candidates(down_top, reports, "down", llm_rank=llm_rank_down)

    top_up = ranked_up[:3]
    top_down = ranked_down[:3]

    # Call #4: summarization
    summary = ""
    try:
        summ = _llm_call(prompt_summarize(gene, top_up, top_down, reports))
        if summ and isinstance(summ, dict):
            summary = summ.get("summary", "")
        log["llm_summary"] = "ok" if summary else "invalid"
    except Exception:
        log["llm_summary"] = "failed"

    return {
        "input_gene": gene,
        "top_up": top_up,
        "top_down": top_down,
        "meta": {
            "alpha": alpha,
            "context": context,
            "log": log,
            "llm_generation": llm_gen or {},
            "llm_modification": llm_mod or {},
            "summary": summary,
        },
    }
