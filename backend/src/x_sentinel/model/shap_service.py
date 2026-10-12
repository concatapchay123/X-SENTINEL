from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from x_sentinel.data.schema import FEATURE_COUNT, validate_vector, validate_vector_batch


@dataclass(frozen=True)
class SHAPExplanation:
    """Canonical representation of local feature attributions for a single sample."""

    values: list[float]
    base_value: float
    raw_score: float
    feature_count: int = FEATURE_COUNT
    feature_names: list[str] | None = None

    def __post_init__(self) -> None:
        if len(self.values) != self.feature_count:
            raise ValueError(
                f"SHAP values dimension mismatch: expected {self.feature_count}, "
                f"got {len(self.values)}"
            )


    def __len__(self) -> int:
        return len(self.values)

    def __getitem__(self, item: Any) -> Any:
        return self.values[item]

    def __iter__(self) -> Iterator[float]:
        return iter(self.values)

    def check_additivity(self, tolerance: float = 1e-4) -> bool:
        """Verify the fundamental efficiency/additivity axiom of local SHAP:

        sum(shap_values) + base_value == raw_score (within tolerance).
        """
        shap_sum = sum(self.values)
        return abs(shap_sum + self.base_value - self.raw_score) <= tolerance

    def to_dict(self) -> dict[str, Any]:
        return {
            "values": self.values,
            "base_value": self.base_value,
            "raw_score": self.raw_score,
            "feature_count": self.feature_count,
            "feature_names": self.feature_names,
        }


class SHAPService:
    """Local SHAP explainer service using native LightGBM TreeSHAP."""

    def __init__(self, feature_count: int = FEATURE_COUNT) -> None:
        self.feature_count = feature_count

    def explain(self, model: Any, vector: Sequence[float]) -> SHAPExplanation:
        """Compute exact TreeSHAP values for a single 2,381-dimensional input vector."""
        valid_vector = validate_vector(vector)
        matrix = np.asarray([valid_vector], dtype=np.float32)

        if hasattr(model, "predict"):
            contrib = model.predict(matrix, pred_contrib=True)
            if contrib.ndim != 2 or contrib.shape[1] != self.feature_count + 1:
                raise ValueError(
                    f"Unexpected TreeSHAP output shape: expected (1, {self.feature_count + 1}), "
                    f"got {contrib.shape}"
                )
            row = contrib[0]
            values = [float(v) for v in row[: self.feature_count]]
            base_val = float(row[self.feature_count])
            raw_sc = float(np.sum(row))

            return SHAPExplanation(
                values=values,
                base_value=base_val,
                raw_score=raw_sc,
                feature_count=self.feature_count,
            )

        raise TypeError(
            f"Model of type '{type(model).__name__}' does not support SHAP predict method"
        )

    def explain_batch(
        self, model: Any, vectors: Sequence[Sequence[float]]
    ) -> list[SHAPExplanation]:
        """Compute exact TreeSHAP values for a batch of 2,381-dimensional input vectors."""
        valid_batch = validate_vector_batch(vectors)
        if not valid_batch:
            return []

        matrix = np.asarray(valid_batch, dtype=np.float32)
        if hasattr(model, "predict"):
            contrib = model.predict(matrix, pred_contrib=True)
            if contrib.ndim != 2 or contrib.shape[1] != self.feature_count + 1:
                raise ValueError(
                    f"Unexpected TreeSHAP output shape: expected (N, {self.feature_count + 1}), "
                    f"got {contrib.shape}"
                )

            explanations: list[SHAPExplanation] = []
            for row in contrib:
                values = [float(v) for v in row[: self.feature_count]]
                base_val = float(row[self.feature_count])
                raw_sc = float(np.sum(row))
                explanations.append(
                    SHAPExplanation(
                        values=values,
                        base_value=base_val,
                        raw_score=raw_sc,
                        feature_count=self.feature_count,
                    )
                )
            return explanations

        raise TypeError(
            f"Model of type '{type(model).__name__}' does not support SHAP predict method"
        )
