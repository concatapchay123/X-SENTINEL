from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import yaml

from x_sentinel.data.schema import FEATURE_COUNT, validate_vector, validate_vector_batch
from x_sentinel.model.demo import DemoModelService, ModelInferenceResult, ModelMetadata
from x_sentinel.model.shap_service import SHAPService


class ModelServiceError(Exception):
    """Base exception for all model service failures."""


class ModelArtifactNotFoundError(ModelServiceError, FileNotFoundError):
    """Raised when the specified model artifact file does not exist on disk."""


class ModelIntegrityError(ModelServiceError, ValueError):
    """Raised when checksum mismatch, file corruption, or unauthorized state is detected."""


class ModelCompatibilityError(ModelServiceError, ValueError):
    """Raised when the model feature dimensions do not match the canonical 2,381 schema."""


class ModelConfigUnresolvedError(ModelServiceError, RuntimeError):
    """Raised when scientific model configuration remains unresolved pending freeze of OQ-02."""


def compute_artifact_sha256(path: Path | str, chunk_size: int = 65536) -> str:
    """Compute deterministic SHA-256 hash for a model artifact file on disk."""
    p = Path(path)
    if not p.is_file():
        raise ModelArtifactNotFoundError(f"Model artifact file does not exist: {p}")

    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


_MODEL_CACHE: dict[tuple[str, str], LightGBMService] = {}


def clear_model_cache() -> None:
    """Clear internal in-memory cache of loaded models."""
    global _MODEL_CACHE
    _MODEL_CACHE.clear()


class LightGBMService:
    """Scientific LightGBM model adapter for X-SENTINEL V3."""

    def __init__(
        self,
        model_path: Path | str,
        expected_sha256: str | None = None,
        version: str = "ember2018-v1",
        feature_count: int = FEATURE_COUNT,
        allow_demo: bool = False,
    ) -> None:
        self.model_path = Path(model_path)
        self.version = version
        self.feature_count = feature_count
        self.allow_demo = allow_demo
        self.demo_mode = False
        self.status = "SCIENTIFIC_APPROVED"

        if not self.model_path.is_file():
            raise ModelArtifactNotFoundError(
                f"Model artifact file does not exist: {self.model_path}"
            )

        self.actual_sha256 = compute_artifact_sha256(self.model_path)
        self.expected_sha256 = expected_sha256.lower() if expected_sha256 else None

        if self.expected_sha256 and self.actual_sha256 != self.expected_sha256:
            raise ModelIntegrityError(
                f"Artifact checksum mismatch for '{self.model_path}': "
                f"expected {self.expected_sha256}, got {self.actual_sha256}"
            )

        try:
            self._booster = lgb.Booster(model_file=str(self.model_path))
        except Exception as exc:
            raise ModelIntegrityError(
                f"Failed to load LightGBM model from '{self.model_path}': {exc}"
            ) from exc

        model_num_features = self._booster.num_feature()
        if model_num_features != self.feature_count:
            raise ModelCompatibilityError(
                f"Model feature count mismatch: expected {self.feature_count}, "
                f"got {model_num_features}"
            )

        self.num_trees = self._booster.num_trees()
        self.objective = "binary sigmoid:1"
        self.shap_service = SHAPService(feature_count=self.feature_count)

    @property
    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            version=self.version,
            status=self.status,
            adapter="lightgbm",
            artifact_path=str(self.model_path),
            artifact_sha256=self.actual_sha256,
            feature_count=self.feature_count,
            objective=self.objective,
            num_trees=self.num_trees,
            parameters={
                "num_trees": self.num_trees,
                "feature_count": self.feature_count,
            },
            notes=["Scientific LightGBM model verified and loaded."],
        )

    def predict_proba(self, vector: Sequence[float]) -> float:
        """Run fast inference returning only probability in [0, 1] without SHAP overhead."""
        valid_vector = validate_vector(vector)
        matrix = np.asarray([valid_vector], dtype=np.float32)
        probs = self._booster.predict(matrix)
        return float(probs[0])

    def infer(self, vector: Sequence[float]) -> ModelInferenceResult:
        """Run deterministic inference and local SHAP on a single 2,381-dimensional vector."""
        valid_vector = validate_vector(vector)
        matrix = np.asarray([valid_vector], dtype=np.float32)

        raw_preds = self._booster.predict(matrix, raw_score=True)
        raw_score = float(raw_preds[0])

        probs = self._booster.predict(matrix)
        score = float(probs[0])

        explanation = self.shap_service.explain(self._booster, valid_vector)

        return ModelInferenceResult(
            score=score,
            shap_values=explanation.values,
            raw_score=raw_score,
            base_value=explanation.base_value,
            model_version=self.version,
            artifact_sha256=self.actual_sha256,
            demo_mode=False,
            status=self.status,
            warnings=[],
            explanation=explanation,
        )

    def infer_batch(self, vectors: Sequence[Sequence[float]]) -> list[ModelInferenceResult]:
        """Run batch inference and local SHAP on a sequence of 2,381-dimensional vectors."""
        valid_batch = validate_vector_batch(vectors)
        if not valid_batch:
            return []

        matrix = np.asarray(valid_batch, dtype=np.float32)
        raw_preds = self._booster.predict(matrix, raw_score=True)
        probs = self._booster.predict(matrix)
        explanations = self.shap_service.explain_batch(self._booster, valid_batch)

        results: list[ModelInferenceResult] = []
        for idx in range(len(valid_batch)):
            score = float(probs[idx])
            raw_score = float(raw_preds[idx])
            expl = explanations[idx]
            results.append(
                ModelInferenceResult(
                    score=score,
                    shap_values=expl.values,
                    raw_score=raw_score,
                    base_value=expl.base_value,
                    model_version=self.version,
                    artifact_sha256=self.actual_sha256,
                    demo_mode=False,
                    status=self.status,
                    warnings=[],
                    explanation=expl,
                )
            )
        return results


def load_model_service(
    config_source: Path | str | dict[str, Any] | None = None,
    allow_demo: bool = True,
    model_cache: bool = True,
) -> LightGBMService | DemoModelService:
    """Authoritative factory function to load a versioned model service from configuration."""
    raw_cfg: dict[str, Any] = {}
    if config_source is None:
        raise ValueError("config_source must be provided to load_model_service")

    if isinstance(config_source, (str, Path)):
        p = Path(config_source)
        if not p.is_file():
            raise FileNotFoundError(f"Model configuration file not found: {p}")
        with open(p, encoding="utf-8") as f:
            raw_cfg = yaml.safe_load(f) or {}
    elif isinstance(config_source, dict):
        raw_cfg = config_source
    else:
        raise TypeError(f"Unsupported config_source type: {type(config_source).__name__}")

    status = raw_cfg.get("status")
    adapter = raw_cfg.get("adapter", "lightgbm")

    if status == "DEMO_ONLY" or adapter == "deterministic_demo":
        if not allow_demo:
            raise ModelIntegrityError("Demo model adapter is not permitted when allow_demo=False")
        return DemoModelService(
            feature_count=raw_cfg.get("feature_count", FEATURE_COUNT),
            random_seed=raw_cfg.get("random_seed", 42),
        )

    if (
        status == "TBD_MUST_FREEZE"
        or raw_cfg.get("model_path") is None
        or raw_cfg.get("model_sha256") is None
    ):
        raise ModelConfigUnresolvedError(
            "Scientific model configuration remains unresolved pending freeze of OQ-02"
        )

    if adapter == "lightgbm":
        raw_path = raw_cfg["model_path"]
        model_path = Path(raw_path)
        if not model_path.is_absolute() and not model_path.exists():
            candidate = Path.cwd() / model_path
            if candidate.exists():
                model_path = candidate

        expected_hash = raw_cfg.get("model_sha256")
        cache_key = (str(model_path.resolve()), str(expected_hash).lower())

        if model_cache and cache_key in _MODEL_CACHE:
            return _MODEL_CACHE[cache_key]

        service = LightGBMService(
            model_path=model_path,
            expected_sha256=expected_hash,
            version=raw_cfg.get("version", "ember2018-v1"),
            feature_count=raw_cfg.get("feature_count", FEATURE_COUNT),
            allow_demo=allow_demo,
        )

        if model_cache:
            _MODEL_CACHE[cache_key] = service

        return service

    raise ValueError(f"Unsupported model adapter: '{adapter}'")
