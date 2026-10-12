from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VectorAnalysisRequest(BaseModel):
    features: list[float] = Field(
        ...,
        description="2,381-dimensional normalized numerical feature vector matching EMBER",
    )
    source_name: str | None = Field(
        default=None,
        description="Optional human-readable source label or file identifier",
    )
    request_id: str | None = Field(
        default=None,
        description="Optional client-provided correlation or idempotency request identifier",
    )


class AnalysisResponse(BaseModel):
    request_id: str = Field(..., description="Unique analysis request identifier")
    status: str = Field(..., description="Analysis status: completed, DEMO_ONLY, or quarantined")
    demo_mode: bool = Field(..., description="Flag indicating whether demo mode was active")
    malware_score: float = Field(
        ..., description="Primary LightGBM malware probability score in [0.0, 1.0]"
    )
    signals: dict[str, float] = Field(
        ..., description="Dictionary of detector signals (m1 through m5)"
    )
    suspicion_score: float = Field(..., description="Fused suspicion score in [0.0, 1.0]")
    threshold: float | None = Field(default=None, description="Applied decision threshold")
    decision: str | None = Field(
        default=None, description="Detector verdict: PASS, ALERT, QUARANTINE, or DEMO_ONLY"
    )
    view_contributions: dict[str, float] = Field(
        default_factory=dict,
        description="Decomposed feature view contributions: structural, behavioral, metadata",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Operational or policy warnings generated during analysis",
    )
    evidence_ref: str | None = Field(
        default=None,
        description="Deterministic SHA-256 evidence hash or evidence storage URI",
    )
    job_id: str | None = Field(
        default=None,
        description="Database primary key UUID of the persisted analysis job",
    )


class AnalysisJobSummary(BaseModel):
    id: str = Field(..., description="UUID of the analysis job")
    request_id: str = Field(..., description="Client or system request identifier")
    status: str = Field(
        ..., description="Job status: completed, failed, quarantined, running, queued"
    )
    input_mode: str = Field(..., description="Input mode: vector or raw_pe")
    demo_mode: bool = Field(..., description="Flag indicating if job ran in demo mode")
    decision: str | None = Field(
        default=None, description="Persisted decision: pass, alert, quarantine, unknown"
    )
    malware_score: float | None = Field(default=None, description="Persisted malware score")
    suspicion_score: float | None = Field(
        default=None, description="Persisted fused suspicion score"
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    completed_at: str | None = Field(default=None, description="ISO 8601 completion timestamp")


class AnalysisHistoryListResponse(BaseModel):
    items: list[AnalysisJobSummary] = Field(
        default_factory=list, description="List of analysis summaries"
    )
    total: int = Field(..., description="Total count of matching records")
    limit: int = Field(..., description="Maximum records requested")
    offset: int = Field(..., description="Record offset requested")


class DetectorScoreItem(BaseModel):
    detector_code: str = Field(..., description="Detector code: M1, M2, M3, M4, or M5")
    score: float = Field(..., description="Numerical score for this detector in [0.0, 1.0]")
    diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic metadata and intermediate calculations for this detector",
    )


class AlertSummary(BaseModel):
    id: str = Field(..., description="Alert UUID")
    analysis_job_id: str = Field(..., description="Associated analysis job UUID")
    severity: str = Field(..., description="Alert severity: low, medium, high, or critical")
    status: str = Field(..., description="Alert status: open, acknowledged, resolved, or dismissed")
    reason: str = Field(..., description="Explanation or detector verdict triggering the alert")
    created_at: str = Field(..., description="ISO 8601 alert creation timestamp")
    resolved_at: str | None = Field(
        default=None, description="ISO 8601 resolution timestamp if resolved"
    )


class AnalysisResultDetail(BaseModel):
    malware_score: float | None = Field(default=None, description="Model malware score")
    suspicion_score: float | None = Field(default=None, description="Fused suspicion score")
    threshold: float | None = Field(default=None, description="Decision threshold applied")
    decision: str = Field(..., description="Persisted decision: pass, alert, quarantine, unknown")
    latency_ms: float | None = Field(
        default=None, description="End-to-end execution latency in milliseconds"
    )
    view_contributions: dict[str, float] = Field(
        default_factory=dict,
        description="Feature view contributions",
    )
    evidence_uri: str | None = Field(
        default=None, description="URI reference to canonical evidence artifact"
    )
    result_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Full serialized result record",
    )


class AnalysisDetailResponse(BaseModel):
    id: str = Field(..., description="UUID of the analysis job")
    request_id: str = Field(..., description="Unique request identifier")
    status: str = Field(..., description="Job status")
    input_mode: str = Field(..., description="Input mode: vector or raw_pe")
    input_sha256: str | None = Field(
        default=None, description="SHA-256 digest of input vector or binary"
    )
    demo_mode: bool = Field(..., description="Demo mode indicator")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    completed_at: str | None = Field(default=None, description="ISO 8601 completion timestamp")
    error_code: str | None = Field(default=None, description="Error code if job failed")
    error_message: str | None = Field(default=None, description="Error message if job failed")
    result: AnalysisResultDetail | None = Field(
        default=None, description="Detailed analysis result record"
    )
    scores: list[DetectorScoreItem] = Field(
        default_factory=list, description="Detector scores M1 through M5"
    )
    alerts: list[AlertSummary] = Field(
        default_factory=list, description="Alerts associated with this analysis"
    )
    evidence_ref: str | None = Field(default=None, description="Evidence digest or reference")


class AlertListResponse(BaseModel):
    items: list[AlertSummary] = Field(default_factory=list, description="List of alert summaries")
    total: int = Field(..., description="Total matching alerts count")
    limit: int = Field(..., description="Query limit")
    offset: int = Field(..., description="Query offset")


class AlertStatusUpdateRequest(BaseModel):
    status: str = Field(
        ...,
        description="Target alert status: acknowledged, resolved, or dismissed",
    )


class CanonicalEvidenceResponse(BaseModel):
    request_id: str = Field(..., description="Unique request identifier")
    run_id: str = Field(..., description="Execution run identifier")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    code_commit: str = Field(..., description="Git commit hash provenance")
    build_digest: str = Field(..., description="Deterministic build artifact digest")
    input_id: str = Field(..., description="SHA-256 digest of input data")
    input_mode: str = Field(..., description="Input mode: vector or raw_pe")
    view_map_hash: str = Field(..., description="SHA-256 digest of view mapping configuration")
    model_hash: str = Field(..., description="SHA-256 digest of active model weights/artifact")
    model_config_hash: str = Field(..., description="SHA-256 digest of model configuration")
    detector_config_hash: str = Field(..., description="SHA-256 digest of detector configuration")
    seed: int = Field(..., description="Random seed used during execution")
    malware_score: float = Field(..., description="LightGBM model inference score")
    signals: dict[str, float] = Field(..., description="Detector signals m1 through m5")
    fusion_score: float = Field(..., description="Calibrated fused suspicion score")
    threshold_id: str = Field(..., description="Identifier of the applied threshold policy")
    decision: str = Field(
        ..., description="Canonical verdict: PASS, ALERT, QUARANTINE, or DEMO_ONLY"
    )
    latency_ms: dict[str, float] = Field(..., description="Latency breakdown in milliseconds")
    demo_mode: bool = Field(..., description="Flag indicating if run was in demo mode")
    evidence_hash: str = Field(
        ..., description="Deterministic SHA-256 digest over the canonical JSON payload"
    )
    verified: bool = Field(
        default=True, description="Integrity verification status (computed digest == stored digest)"
    )


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable canonical error code")
    message: str = Field(..., description="Human-readable error description")


class ErrorResponse(BaseModel):
    detail: ErrorDetail = Field(..., description="Structured error payload")
