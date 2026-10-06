from __future__ import annotations

from pydantic import BaseModel, Field


class VectorAnalysisRequest(BaseModel):
    features: list[float]
    source_name: str | None = None
    request_id: str | None = None


class AnalysisResponse(BaseModel):
    request_id: str
    status: str
    demo_mode: bool
    malware_score: float
    signals: dict[str, float]
    suspicion_score: float
    threshold: float | None
    view_contributions: dict[str, float]
    warnings: list[str] = Field(default_factory=list)
    evidence_ref: str | None = None
