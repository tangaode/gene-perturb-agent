from typing import List, Literal
from pydantic import BaseModel, Field


class PerturbRequest(BaseModel):
    gene: str
    alpha: float = 1.0
    context: str = "default"


class GeneResult(BaseModel):
    gene: str
    effect_score: float = Field(..., ge=0)
    delta_sign: Literal["up", "down"]
    p_up: float = Field(..., ge=0, le=1)
    p_down: float = Field(..., ge=0, le=1)


class PerturbResponse(BaseModel):
    input_gene: str
    context: str
    results: List[GeneResult]
