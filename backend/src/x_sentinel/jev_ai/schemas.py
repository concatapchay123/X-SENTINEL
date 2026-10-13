from __future__ import annotations

import math
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


class JevFailureClassification(BaseModel):
    error_code: str
    db_status: str
    http_status: int
    retryable: bool = False
    message: str
    advisory_only: bool = True

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("JevFailureClassification must be advisory_only=True")
        return True


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
        if not isinstance(v, str):
            raise ValueError("Option id and label must be strings")
        if "\n" in v or "\r" in v:
            raise ValueError("Option id and label must not contain newline characters")
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

    @field_validator("letter")
    @classmethod
    def validate_letter(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) != 1 or not ("A" <= clean <= "Z"):
            raise ValueError(f"Option letter must be single uppercase A-Z; got '{v}'")
        return clean

    @field_validator("logprob", mode="before")
    @classmethod
    def validate_logprob(cls, v: Any) -> float:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"Logprob must be a finite number; got {v!r}")
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            raise ValueError(f"Logprob must be finite; got {fv}")
        if fv > 1e-5:
            raise ValueError(f"Logprob cannot be positive (> 0); got {fv}")
        return min(fv, 0.0)

    @field_validator("probability", mode="before")
    @classmethod
    def validate_prob_range(cls, v: Any) -> float:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"Probability must be a finite number; got {v!r}")
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            raise ValueError(f"Probability must be finite; got {fv}")
        if fv < -1e-6 or fv > 1.000001:
            raise ValueError(f"Probability must be within [0, 1]; got {fv}")
        return min(max(fv, 0.0), 1.0)


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

    @field_validator("score_levels", mode="before")
    @classmethod
    def validate_score_levels_numeric(cls, v: Any) -> list[float] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("score_levels must be a list of finite numbers")
        cleaned: list[float] = []
        for item in v:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError(f"score_levels elements must be numeric (not bool); got {item!r}")
            fv = float(item)
            if math.isnan(fv) or math.isinf(fv):
                raise ValueError(f"score_levels elements must be finite; got {fv}")
            cleaned.append(fv)
        return cleaned

    @model_validator(mode="after")
    def validate_decision_type_constraints(self) -> TypedDecisionRequest:
        if self.decision_type == DecisionType.BOOL:
            if len(self.options) != 2:
                raise ValueError(
                    f"Bool decisions require exactly 2 options (yes/no); got {len(self.options)}"
                )
            if self.score_levels is not None:
                raise ValueError("score_levels must not be provided for Bool decisions")
            opt_a_tokens = {
                self.options[0].id.strip().lower(),
                self.options[0].label.strip().lower(),
            }
            opt_b_tokens = {
                self.options[1].id.strip().lower(),
                self.options[1].label.strip().lower(),
            }
            negative_markers = {"no", "false", "0", "negative"}
            positive_markers = {"yes", "true", "1", "positive"}
            if (opt_a_tokens & negative_markers) or (opt_b_tokens & positive_markers):
                raise ValueError(
                    "Bool decisions require Option A to be affirmative (Yes/True) and "
                    "Option B to be negative (No/False)"
                )
        elif self.decision_type == DecisionType.CHOICE:
            if self.score_levels is not None:
                raise ValueError("score_levels must not be provided for Choice decisions")
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
    request_id: str | None = None
    context_digest: str | None = None
    prompt_digest: str | None = None
    output_digest: str | None = None
    validation_status: str = "completed"

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_immutable(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Jev AI decisions must be advisory_only=True; authority escalation forbidden"
            )
        return True

    @field_validator("selected_letter")
    @classmethod
    def validate_selected_letter(cls, v: str) -> str:
        if not isinstance(v, str) or len(v) != 1 or not ("A" <= v <= "Z"):
            raise ValueError(f"selected_letter must be a single uppercase letter A-Z; got {v!r}")
        return v

    @model_validator(mode="after")
    def validate_cross_type_isolation(self) -> TypedDecisionResponse:
        if self.probabilities:
            prob_sum = sum(p.probability for p in self.probabilities)
            if abs(prob_sum - 1.0) > 1e-4:
                raise ValueError(
                    f"TypedDecisionResponse probabilities must sum to 1.0; got {prob_sum}"
                )
            letters = [p.letter for p in self.probabilities]
            if len(set(letters)) != len(letters):
                raise ValueError(f"Duplicate option letters in probabilities: {letters}")
            matched = [p for p in self.probabilities if p.letter == self.selected_letter]
            if not matched:
                raise ValueError(
                    f"selected_letter '{self.selected_letter}' not found in probabilities"
                )
            if matched[0].option_id != self.selected_option_id:
                raise ValueError(
                    f"selected_option_id '{self.selected_option_id}' does not match "
                    f"selected_letter '{self.selected_letter}' option_id '{matched[0].option_id}'"
                )

        if self.decision_type == DecisionType.CHOICE:
            if self.bool_value is not None or self.expected_score is not None:
                raise ValueError(
                    "CHOICE decision response must not populate bool_value or expected_score"
                )
        elif self.decision_type == DecisionType.BOOL:
            if self.expected_score is not None:
                raise ValueError("BOOL decision response must not populate expected_score")
            if not isinstance(self.bool_value, bool):
                raise ValueError("BOOL decision response requires bool_value to be a boolean")
            expected_bool = self.selected_letter == "A"
            if self.bool_value is not expected_bool:
                raise ValueError(
                    f"BOOL decision response bool_value ({self.bool_value}) must match "
                    f"selected_letter == 'A' ({expected_bool})"
                )
        elif self.decision_type == DecisionType.SCORE:
            if self.bool_value is not None:
                raise ValueError("SCORE decision response must not populate bool_value")
            if (
                self.expected_score is None
                or math.isnan(self.expected_score)
                or math.isinf(self.expected_score)
            ):
                raise ValueError("SCORE decision response requires a finite expected_score")
        return self


class ExplainResult(BaseModel):
    analysis_id: str | None = None
    request_id: str | None = None
    workflow: str = "explain"
    summary: str
    evidence_breakdown: dict[str, Any] = Field(default_factory=dict)
    key_factors: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    advisory_decision: TypedDecisionResponse | None = None
    advisory_only: bool = True
    input_digest: str
    output_digest: str | None = None
    model_id: str = "jev-local-TBD"
    prompt_version: str = "jev-v3.0.0"
    validation_status: str = "completed"
    latency_ms: float | None = None

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("ExplainResult must be advisory_only=True")
        return True


ALLOWED_TRIAGE_PRIORITIES = frozenset(
    {
        "immediate_review",
        "standard_review",
        "low_priority",
        "routine_verification",
        "immediate_escalation",
        "manual_deep_inspection",
        "standard_queue_review",
        "low_priority_monitor",
    }
)


class TriageResult(BaseModel):
    analysis_id: str | None = None
    request_id: str | None = None
    workflow: str = "triage"
    priority_category: str
    priority_label: str = ""
    advisory_decision: TypedDecisionResponse
    detector_verdict: str | None = None
    detector_malware_score: float | None = None
    recommended_analyst_action: str
    advisory_only: bool = True
    input_digest: str
    output_digest: str | None = None
    model_id: str = "jev-local-TBD"
    prompt_version: str = "jev-v3.0.0"
    validation_status: str = "completed"
    latency_ms: float | None = None

    @field_validator("priority_category")
    @classmethod
    def validate_priority_category(cls, v: str) -> str:
        clean = v.strip() if isinstance(v, str) else ""
        if clean not in ALLOWED_TRIAGE_PRIORITIES:
            allowed_list = sorted(ALLOWED_TRIAGE_PRIORITIES)
            raise ValueError(f"Invalid priority_category '{v}'; must be one of {allowed_list}")
        return clean

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("TriageResult must be advisory_only=True")
        return True


class CompareResult(BaseModel):
    baseline_id: str | None = None
    candidate_id: str | None = None
    request_id: str | None = None
    workflow: str = "compare"
    deterministic_diff: dict[str, Any] = Field(default_factory=dict)
    advisory_decision: TypedDecisionResponse | None = None
    comparison_summary: str
    advisory_only: bool = True
    input_digest: str
    output_digest: str | None = None
    model_id: str = "jev-local-TBD"
    prompt_version: str = "jev-v3.0.0"
    validation_status: str = "completed"
    latency_ms: float | None = None

    @field_validator("advisory_only")
    @classmethod
    def enforce_advisory_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("CompareResult must be advisory_only=True")
        return True


class ReportResult(BaseModel):
    analysis_id: str | None = None
    request_id: str | None = None
    workflow: str = "report"
    title: str = "Analysis Advisory Report"
    timestamp: str
    detector_summary: dict[str, Any] = Field(default_factory=dict)
    advisory_assessment: dict[str, Any] = Field(default_factory=dict)
    limitations_disclaimer: str
    markdown_content: str
    advisory_only: bool = True
    input_digest: str
    output_digest: str | None = None
    model_id: str = "jev-local-TBD"
    prompt_version: str = "jev-v3.0.0"
    validation_status: str = "completed"
    latency_ms: float | None = None

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
