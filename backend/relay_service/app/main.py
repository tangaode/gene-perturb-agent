import os
import time
from collections import defaultdict, deque
from typing import Any, Dict

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LLM Relay Service")

origins = [x.strip() for x in os.environ.get("CORS_ORIGINS", "*").split(",") if x.strip()]
if origins == ["*"] or not origins:
    origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEFAULT_MODEL = os.environ.get("RELAY_DEFAULT_MODEL", "deepseek-chat")
RELAY_API_KEY = os.environ.get("RELAY_API_KEY", "")
REQUEST_TIMEOUT = int(os.environ.get("RELAY_TIMEOUT", "120"))
RPM = int(os.environ.get("RELAY_RPM", "120"))

# naive in-memory limiter: per client key, rolling 60s
_BUCKETS = defaultdict(deque)


def _client_key(req: Request) -> str:
    auth = req.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()[:64] or "anon"
    fwd = req.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


def _check_auth(req: Request):
    if not RELAY_API_KEY:
        return
    auth = req.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth[7:].strip()
    if token != RELAY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid token")


def _check_rate_limit(req: Request):
    k = _client_key(req)
    now = time.time()
    q = _BUCKETS[k]
    while q and (now - q[0]) > 60:
        q.popleft()
    if len(q) >= RPM:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    q.append(now)


def _forward_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="Server missing DEEPSEEK_API_KEY")

    if "model" not in payload or not payload.get("model"):
        payload["model"] = DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        detail = "Upstream error"
        try:
            detail = e.response.text
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_v1(req: Request):
    _check_auth(req)
    _check_rate_limit(req)
    payload = await req.json()
    return _forward_chat(payload)


@app.post("/chat/completions")
async def chat_compat(req: Request):
    _check_auth(req)
    _check_rate_limit(req)
    payload = await req.json()
    return _forward_chat(payload)
