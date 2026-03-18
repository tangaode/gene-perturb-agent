from typing import List, Literal
from pydantic import BaseModel, Field


class Candidate(BaseModel):
    gene: str
    direction: Literal["up", "down"]


class VerifyBatchRequest(BaseModel):
    input_gene: str
    candidates: List[Candidate]


class EvidenceItem(BaseModel):
    source: str
    text: str
    meta: dict = Field(default_factory=dict)


class VerifyReport(BaseModel):
    gene: str
    direction: str
    evidence_rel: float = Field(..., ge=0, le=1)
    evidence_dir: float = Field(..., ge=0, le=1)
    items: List[EvidenceItem]


class VerifyBatchResponse(BaseModel):
    reports: List[VerifyReport]
