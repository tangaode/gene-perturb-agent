import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import RunRequest, RunResponse
from .orchestrator import run_pipeline

app = FastAPI(title="Gene Perturbation Agent API")

origins_env = os.environ.get("CORS_ORIGINS", "*")
origins = [o.strip() for o in origins_env.split(",") if o.strip()]
if origins_env.strip() == "*":
    origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def run(req: RunRequest):
    try:
        return run_pipeline(req.gene, req.alpha, req.context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
