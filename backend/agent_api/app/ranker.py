from typing import List, Dict


def _minmax(vals):
    if not vals:
        return []
    vmin = min(vals)
    vmax = max(vals)
    if vmax - vmin < 1e-9:
        return [0.0 for _ in vals]
    return [(v - vmin) / (vmax - vmin) for v in vals]


def rank_candidates(candidates: List[Dict], reports: List[Dict], direction: str, llm_rank: Dict[str, float] | None = None):
    report_map = {(r["gene"], r["direction"]): r for r in reports}
    scores = []
    effect_vals = [c.get("effect_score", 0.0) for c in candidates]
    effect_norm = _minmax(effect_vals)

    for idx, c in enumerate(candidates):
        gene = c["gene"]
        report = report_map.get((gene, direction), {})
        evidence_rel = float(report.get("evidence_rel", 0.0))
        evidence_dir = float(report.get("evidence_dir", 0.0))
        model_strength = effect_norm[idx]
        model_dirprob = float(c.get("p_up" if direction == "up" else "p_down", 0.0))
        llm_score = 0.0
        if llm_rank:
            llm_score = float(llm_rank.get(gene, 0.0))

        score = (
            0.30 * model_strength
            + 0.20 * model_dirprob
            + 0.30 * evidence_rel
            + 0.10 * evidence_dir
            + 0.10 * llm_score
        )

        scores.append({
            "gene": gene,
            "score": score,
            "confidence": max(model_dirprob, evidence_rel),
            "evidence": report.get("items", []),
            "model_dirprob": model_dirprob,
            "evidence_rel": evidence_rel,
            "llm_score": llm_score,
        })

    # hard rule
    filtered = [
        s for s in scores
        if not (s["evidence_rel"] == 0 and s["model_dirprob"] < 0.7)
    ]
    if not filtered:
        filtered = scores
    ranked = sorted(filtered, key=lambda x: x["score"], reverse=True)
    return ranked
