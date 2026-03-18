from fastapi import FastAPI

from .schemas import PerturbRequest, PerturbResponse
from .model_runner import run_virtualcell

app = FastAPI(title="VirtualCell Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/perturb", response_model=PerturbResponse)
def perturb(req: PerturbRequest):
    results = run_virtualcell(req.gene, req.alpha, req.context)
    return PerturbResponse(input_gene=req.gene, context=req.context, results=results)
