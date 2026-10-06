from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JevMode(StrEnum):
    EXPLAIN = "explain"
    TRIAGE = "triage"
    COMPARE = "compare"
    REPORT = "report"
    DOCS = "docs"


class JevContext(BaseModel):
    analysis_id: str | None = None
    request_id: str | None = None
    decision: str | None = None
    malware_score: float | None = None
    suspicion_score: float | None = None
    threshold: float | None = None
    detector_scores: dict[str, float] = Field(default_factory=dict)
    detector_diagnostics: dict[str, Any] = Field(default_factory=dict)
    view_contributions: dict[str, float] = Field(default_factory=dict)
    top_shap: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class JevRequest(BaseModel):
    mode: JevMode = JevMode.EXPLAIN
    context: JevContext
    question: str | None = None


class JevResponse(BaseModel):
    text: str
    model_id: str
    prompt_version: str
    advisory_only: bool = True
    latency_ms: float | None = None
    raw: dict[str, Any] | None = None
