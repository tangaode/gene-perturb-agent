from typing import List, Dict
import os

UP_P_THRESHOLD = float(os.environ.get("UP_P_THRESHOLD", "0.6"))
DOWN_P_THRESHOLD = float(os.environ.get("DOWN_P_THRESHOLD", "0.6"))
TOPN_CANDIDATES = int(os.environ.get("TOPN_CANDIDATES", "50"))


def filter_candidates(results: List[Dict]):
    up = []
    down = []
    for r in results:
        if r.get("delta_sign") == "up" and r.get("p_up", 0) >= UP_P_THRESHOLD:
            score = r.get("effect_score", 0) * r.get("p_up", 0)
            up.append({**r, "rank_score": score})
        if r.get("delta_sign") == "down" and r.get("p_down", 0) >= DOWN_P_THRESHOLD:
            score = r.get("effect_score", 0) * r.get("p_down", 0)
            down.append({**r, "rank_score": score})

    up = sorted(up, key=lambda x: x["rank_score"], reverse=True)[:TOPN_CANDIDATES]
    down = sorted(down, key=lambda x: x["rank_score"], reverse=True)[:TOPN_CANDIDATES]
    return up, down
