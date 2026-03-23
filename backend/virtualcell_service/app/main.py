import logging

from fastapi import FastAPI, HTTPException

from .schemas import PerturbRequest, PerturbResponse
from .model_runner import run_virtualcell

app = FastAPI(title="VirtualCell Service")
logger = logging.getLogger("virtualcell_service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/perturb", response_model=PerturbResponse)
def perturb(req: PerturbRequest):
    try:
        results = run_virtualcell(req.gene, req.alpha, req.context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unhandled error in /perturb for gene=%s alpha=%s context=%s", req.gene, req.alpha, req.context)
        raise HTTPException(status_code=500, detail=f"virtualcell failed unexpectedly: {e}")
    return PerturbResponse(input_gene=req.gene, context=req.context, results=results)
