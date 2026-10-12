from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

from x_sentinel.data.schema import FEATURE_COUNT, validate_vector, validate_vector_batch
from x_sentinel.model.shap_service import SHAPExplanation


@dataclass(frozen=True)
class ModelMetadata:
    """Authoritative metadata and provenance for a model service instance."""

    version: str
    status: str
    adapter: str
    artifact_path: str | None
    artifact_sha256: str
    feature_count: int
    objective: str | None = None
    num_trees: int | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ModelInferenceResult:
    """Canonical typed inference result produced by model services."""

    score: float
    shap_values: list[float]
    raw_score: float
    base_value: float
    model_version: str
    artifact_sha256: str
    demo_mode: bool
    status: str
    warnings: list[str] = field(default_factory=list)
    explanation: SHAPExplanation | None = None

    def __iter__(self) -> Iterator[Any]:
        """Allows unpacking as `score, shap = service.infer(vector)` for backward compatibility."""
        yield self.score
        yield self.shap_values

    def __float__(self) -> float:
        """Allows direct numeric casting to float returning model inference score."""
        return float(self.score)


class DemoModelService:
    """Deterministic integration adapter. NOT scientific evidence."""

    def __init__(self, feature_count: int = FEATURE_COUNT, random_seed: int = 42) -> None:
        self.feature_count = feature_count
        self.random_seed = random_seed
        self.demo_mode = True
        self.status = "DEMO_ONLY"
        self.version = "demo-deterministic-v1"
        self.artifact_sha256 = "DEMO_MOCK_NO_ARTIFACT"

    @property
    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            version=self.version,
            status=self.status,
            adapter="deterministic_demo",
            artifact_path=None,
            artifact_sha256=self.artifact_sha256,
            feature_count=self.feature_count,
            objective="pseudo_logistic",
            num_trees=0,
            parameters={"random_seed": self.random_seed},
            notes=["No scientific claim may use this adapter."],
        )

    def infer(self, vector: Sequence[float]) -> ModelInferenceResult:
        valid_vector = validate_vector(vector)
        n = max(len(valid_vector), 1)
        mean = sum(valid_vector) / n
        clamped_mean = max(min(mean, 20.0), -20.0)
        score = 1.0 / (1.0 + math.exp(-clamped_mean))
        shap = [float(v - mean) / n for v in valid_vector]
        raw_score = clamped_mean
        base_value = 0.0

        explanation = SHAPExplanation(
            values=shap,
            base_value=base_value,
            raw_score=raw_score,
            feature_count=len(valid_vector),
        )

        return ModelInferenceResult(
            score=float(score),
            shap_values=shap,
            raw_score=float(raw_score),
            base_value=float(base_value),
            model_version=self.version,
            artifact_sha256=self.artifact_sha256,
            demo_mode=True,
            status="DEMO_ONLY",
            warnings=["DEMO_MODE_NOT_SCIENTIFIC_EVIDENCE"],
            explanation=explanation,
        )

    def predict_proba(self, vector: Sequence[float]) -> float:
        """Lightweight prediction returning only malware probability without SHAP overhead."""
        valid_vector = validate_vector(vector)
        n = max(len(valid_vector), 1)
        mean = sum(valid_vector) / n
        clamped_mean = max(min(mean, 20.0), -20.0)
        return float(1.0 / (1.0 + math.exp(-clamped_mean)))

    def infer_batch(self, vectors: Sequence[Sequence[float]]) -> list[ModelInferenceResult]:
        valid_batch = validate_vector_batch(vectors)
        return [self.infer(vec) for vec in valid_batch]
