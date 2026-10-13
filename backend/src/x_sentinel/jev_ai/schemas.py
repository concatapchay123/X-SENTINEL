from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class JevMode(StrEnum):
    EXPLAIN = "explain"
    TRIAGE = "triage"
    COMPARE = "compare"
    REPORT = "report"
    DOCS = "docs"


class JevStatus(StrEnum):
    DISABLED = "disabled"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    MISCONFIGURED = "misconfigured"


class DecisionType(StrEnum):
    CHOICE = "choice"
    BOOL = "bool"
    SCORE = "score"


class JevStatusResponse(BaseModel):
    enabled: bool
    status: JevStatus
    advisory_only: bool = True
    model_id: str | None = None
    prompt_version: str
    endpoint_label: str = "lm_studio_local"
    readiness_blocking: bool = False
    error: str | None = None


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


class DecisionOption(BaseModel):
    id: str
    label: str

    @field_validator("id", "label")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Option id and label must not be empty or whitespace")
        return clean


class OptionProbability(BaseModel):
    letter: str
    option_id: str
    label: str
    logprob: float
    probability: float

    @field_validator("probability")
    @classmethod
    def validate_prob_range(cls, v: float) -> float:
        if v < -1e-6 or v > 1.000001:
            raise ValueError(f"Probability must be within [0, 1]; got {v}")
        return min(max(v, 0.0), 1.0)


class TypedDecisionRequest(BaseModel):
    decision_type: DecisionType = DecisionType.CHOICE
    state: str
    question: str
    options: list[DecisionOption]
    score_levels: list[float] | None = None
    context_digest: str | None = None

    @field_validator("state", "question")
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("State and question must not be empty or whitespace")
        return clean

    @field_validator("options")
    @classmethod
    def validate_options_list(cls, v: list[DecisionOption]) -> list[DecisionOption]:
        if len(v) < 2:
            raise ValueError(f"At least 2 options required for decision; got {len(v)}")
        if len(v) > 26:
            raise ValueError(f"At most 26 options supported (A-Z); got {len(v)}")
        seen_ids: set[str] = set()
        for opt in v:
            if opt.id in seen_ids:
                raise ValueError(f"Duplicate option id: '{opt.id}'")
            seen_ids.add(opt.id)
        return v

    @model_validator(mode="after")
    def validate_decision_type_constraints(self) -> TypedDecisionRequest:
        if self.decision_type == DecisionType.BOOL:
            if len(self.options) != 2:
                raise ValueError(
                    f"Bool decisions require exactly 2 options (yes/no); got {len(self.options)}"
                )
        elif self.decision_type == DecisionType.SCORE:
            if self.score_levels is None:
                raise ValueError("Score decisions require 'score_levels' to be specified")
            if len(self.score_levels) != len(self.options):
                raise ValueError(
                    f"score_levels count ({len(self.score_levels)}) "
                    f"must match options count ({len(self.options)})"
                )
            for i in range(len(self.score_levels) - 1):
                if self.score_levels[i] > self.score_levels[i + 1]:
                    raise ValueError(
                        f"score_levels must be non-decreasing; got {self.score_levels}"
                    )
        return self


class TypedDecisionResponse(BaseModel):
    decision_type: DecisionType
    selected_letter: str
    selected_option_id: str
    selected_label: str
    probabilities: list[OptionProbability]
    probability_distribution: dict[str, float] = Field(default_factory=dict)
    expected_score: float | None = None
    bool_value: bool | None = None
    model_id: str
    prompt_version: str
    advisory_only: bool = True
    latency_ms: float | None = None
    raw_tokens: list[dict[str, Any]] | None = None

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_immutable(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Jev AI decisions must be advisory_only=True; authority escalation forbidden"
            )
        return True


class ExplainResult(BaseModel):
    analysis_id: str | None = None
    summary: str
    evidence_breakdown: dict[str, Any] = Field(default_factory=dict)
    key_factors: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    advisory_decision: TypedDecisionResponse | None = None
    advisory_only: bool = True
    input_digest: str

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("ExplainResult must be advisory_only=True")
        return True


class TriageResult(BaseModel):
    analysis_id: str | None = None
    priority_category: str
    priority_label: str
    advisory_decision: TypedDecisionResponse
    detector_verdict: str | None = None
    detector_malware_score: float | None = None
    recommended_analyst_action: str
    advisory_only: bool = True
    input_digest: str

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("TriageResult must be advisory_only=True")
        return True


class CompareResult(BaseModel):
    baseline_id: str | None = None
    candidate_id: str | None = None
    deterministic_diff: dict[str, Any] = Field(default_factory=dict)
    advisory_decision: TypedDecisionResponse | None = None
    comparison_summary: str
    advisory_only: bool = True
    input_digest: str

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("CompareResult must be advisory_only=True")
        return True


class ReportResult(BaseModel):
    analysis_id: str | None = None
    title: str = "Analysis Advisory Report"
    timestamp: str
    detector_summary: dict[str, Any] = Field(default_factory=dict)
    advisory_assessment: dict[str, Any] = Field(default_factory=dict)
    limitations_disclaimer: str
    markdown_content: str
    advisory_only: bool = True
    input_digest: str

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("ReportResult must be advisory_only=True")
        return True


class JevResponse(BaseModel):
    text: str
    model_id: str
    prompt_version: str
    advisory_only: bool = True
    latency_ms: float | None = None
    raw: dict[str, Any] | None = None
    logprobs: dict[str, Any] | None = None
    decision: TypedDecisionResponse | None = None

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("JevResponse must be advisory_only=True")
        return True
