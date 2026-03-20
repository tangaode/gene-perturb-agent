import os
import requests

BACKEND = os.environ.get("LLM_BACKEND", "deepseek").lower()
BASE = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1")

OPENAI_BASE = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
OPENAI_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
OPENAI_KEY = os.environ.get("LLM_API_KEY", "")

def _proxies():
    target = BASE if BACKEND == "ollama" else OPENAI_BASE
    if "localhost" in target or "127.0.0.1" in target:
        return {"http": "", "https": ""}
    return None


def list_models():
    if BACKEND == "ollama":
        resp = requests.get(f"{BASE}/api/tags", timeout=15, proxies=_proxies())
        resp.raise_for_status()
        return resp.json()
    # OpenAI-compatible fallback: no model-list endpoint contract, return configured model.
    return {"models": [{"name": OPENAI_MODEL}]}


def chat(messages, options=None):
    if BACKEND == "ollama":
        payload = {
            "model": MODEL,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        resp = requests.post(f"{BASE}/api/chat", json=payload, timeout=120, proxies=_proxies())
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    if not OPENAI_KEY and BACKEND in ("deepseek", "openai", "qwen"):
        raise ValueError("LLM_API_KEY is required when LLM_BACKEND is deepseek/openai/qwen")

    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    headers = {"Content-Type": "application/json"}
    if OPENAI_KEY:
        headers["Authorization"] = f"Bearer {OPENAI_KEY}"
    resp = requests.post(
        f"{OPENAI_BASE}/chat/completions",
        json=payload,
        headers=headers,
        timeout=120,
        proxies=_proxies(),
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
