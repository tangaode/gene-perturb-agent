import json


def system_prompt_json():
    return (
        "You are a biomedical assistant. Output ONLY valid JSON. "
        "No markdown, no extra text."
    )


def prompt_generation(input_gene, up_list, down_list):
    payload = {
        "task": "generation",
        "input_gene": input_gene,
        "up_candidates": up_list,
        "down_candidates": down_list,
        "instructions": {
            "select_top_up": 10,
            "select_top_down": 10,
            "for_each_selected": ["confidence(0-1)", "claim (short, verifiable)"],
            "output_schema": {
                "top_up": [{"gene": "", "confidence": 0.0, "claim": ""}],
                "top_down": [{"gene": "", "confidence": 0.0, "claim": ""}],
            },
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def prompt_modify(input_gene, gen_output, verify_reports):
    payload = {
        "task": "modification",
        "input_gene": input_gene,
        "generation_output": gen_output,
        "verification_reports": verify_reports,
        "instructions": {
            "revise_top_up": 10,
            "revise_top_down": 10,
            "use_evidence": True,
            "output_schema": {
                "top_up": [{"gene": "", "confidence": 0.0, "claim": ""}],
                "top_down": [{"gene": "", "confidence": 0.0, "claim": ""}],
                "final_top_up": ["G1", "G2", "G3"],
                "final_top_down": ["G1", "G2", "G3"],
            },
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def prompt_summarize(input_gene, top_up, top_down, evidence):
    payload = {
        "task": "summarization",
        "input_gene": input_gene,
        "top_up": top_up,
        "top_down": top_down,
        "evidence": evidence,
        "instructions": {
            "summary": "1-3 sentences, short and precise",
            "output_schema": {"summary": ""},
        },
    }
    return json.dumps(payload, ensure_ascii=False)
