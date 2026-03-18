from typing import List
from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    gene: str
    alpha: float = 1.0
    context: str = "default"


class RankedGene(BaseModel):
    gene: str
    score: float
    confidence: float
    evidence: List[dict]


class RunResponse(BaseModel):
    input_gene: str
    top_up: List[RankedGene]
    top_down: List[RankedGene]
    meta: dict = Field(default_factory=dict)
