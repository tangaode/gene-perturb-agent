from fastapi import FastAPI, HTTPException

from .schemas import PerturbRequest, PerturbResponse
from .model_runner import run_virtualcell

app = FastAPI(title="VirtualCell Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/perturb", response_model=PerturbResponse)
def perturb(req: PerturbRequest):
    try:
        results = run_virtualcell(req.gene, req.alpha, req.context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="virtualcell failed unexpectedly")
    return PerturbResponse(input_gene=req.gene, context=req.context, results=results)
