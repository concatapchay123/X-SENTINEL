from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from x_sentinel.evaluation.metrics import (
    CANONICAL_DECISIONS,
    POSITIVE_DETECTOR_DECISIONS,
    ASRResult,
    FPRResult,
    LatencySummary,
    RecallResult,
    compute_asr,
    compute_auroc,
    compute_fpr,
    compute_latency_summary,
    compute_recall,
)
from x_sentinel.evaluation.statistics import validate_unique_sample_ids


class EvaluationRole(StrEnum):
    """Strict role separation for blind scientific evaluation (Task 14.14)."""

    ATTACK_CONSTRUCTION = "ATTACK_CONSTRUCTION"
    DEFENSE_DETECTOR = "DEFENSE_DETECTOR"
    EVALUATION_SCORING = "EVALUATION_SCORING"


class BlindProtocolViolationError(PermissionError):
    """Base error raised when a blind evaluation security or custody invariant is violated."""


class ManifestAccessDeniedError(BlindProtocolViolationError):
    """Raised when the defense detector role attempts to access attack manifests or ground truth."""


class BlindLabelLeakageError(BlindProtocolViolationError):
    """Raised when blind labels or hidden cohort metadata are present in a defense payload."""


class ForbiddenEnvironmentExposureError(BlindProtocolViolationError):
    """Raised when forbidden blind ground-truth environment variables are exposed to defense."""


class BlindCustodyIntegrityError(BlindProtocolViolationError):
    """Raised when a sealed package or ground-truth manifest fails SHA-256 verification."""


class BlindRolePermissionError(BlindProtocolViolationError):
    """Raised when an unauthorized role attempts to run restricted evaluation scoring."""


class PostHocTuningForbiddenError(BlindProtocolViolationError):
    """Raised when post-hoc threshold tuning or decision manipulation is detected."""


FORBIDDEN_DEFENSE_KEYS: frozenset[str] = frozenset(
    {
        "blind_label",
        "ground_truth",
        "eval_label",
        "label",
        "labels",
        "is_malware",
        "y_true",
        "true_label",
        "target_label",
        "trigger_manifest",
        "poison_manifest",
        "hidden_cohort",
        "poisoned_indices",
        "trigger_indices",
        "attack_manifest",
        "is_poisoned",
        "clean_model_score",
        "poisoned_triggered_score",
    }
)

FORBIDDEN_DEFENSE_ENV_VARS: frozenset[str] = frozenset(
    {
        "XS_BLIND_GROUND_TRUTH_PATH",
        "XS_POISON_MANIFEST_PATH",
        "XS_ATTACK_CUSTODY_KEY",
        "XS_BLIND_EVAL_LABELS",
    }
)

FORBIDDEN_FILENAME_TOKENS: tuple[str, ...] = (
    "manifest",
    "ground_truth",
    "blind_label",
    "poison_spec",
)


class BlindCustodyGuard:
    """Enforces custody isolation so the defense detector never accesses manifests or labels."""

    def __init__(
        self,
        role: EvaluationRole,
        restricted_custody_paths: Sequence[Path | str] | None = None,
    ) -> None:
        self.role = role
        self.restricted_custody_paths: tuple[Path, ...] = tuple(
            Path(p).resolve() for p in (restricted_custody_paths or ())
        )

    def assert_path_allowed(self, target_path: Path | str) -> None:
        """Blocks DEFENSE_DETECTOR from reading restricted custody directories or manifest files."""
        if self.role != EvaluationRole.DEFENSE_DETECTOR:
            return
        resolved = Path(target_path).resolve()
        for custody_dir in self.restricted_custody_paths:
            if resolved == custody_dir or custody_dir in resolved.parents:
                raise ManifestAccessDeniedError(
                    f"Defense role is forbidden from accessing restricted custody path: {resolved}"
                )
        name_lower = resolved.name.lower()
        for token in FORBIDDEN_FILENAME_TOKENS:
            if token in name_lower:
                raise ManifestAccessDeniedError(
                    "Forbidden manifest/ground-truth file access attempted "
                    f"by defense role: {resolved.name}"
                )

    def assert_defense_input_clean(self, payload: Mapping[str, Any]) -> None:
        """Blocks DEFENSE_DETECTOR from receiving blind labels, manifests, or cohort tags."""
        if self.role != EvaluationRole.DEFENSE_DETECTOR:
            return

        def _walk(node: Any) -> None:
            if isinstance(node, Mapping):
                for key, val in node.items():
                    key_norm = str(key).strip().lower()
                    if key_norm in FORBIDDEN_DEFENSE_KEYS:
                        raise BlindLabelLeakageError(
                            f"Forbidden blind evaluation key '{key}' "
                            "leaked into defense input payload."
                        )
                    _walk(val)
            elif isinstance(node, (list, tuple)):
                for item in node:
                    _walk(item)

        _walk(payload)

    def assert_environment_clean(self, env: Mapping[str, str] | None = None) -> None:
        """Blocks DEFENSE_DETECTOR execution if forbidden blind custody env vars exist."""
        if self.role != EvaluationRole.DEFENSE_DETECTOR:
            return
        target_env = os.environ if env is None else env
        for var_name in FORBIDDEN_DEFENSE_ENV_VARS:
            if var_name in target_env and str(target_env[var_name]).strip():
                raise ForbiddenEnvironmentExposureError(
                    f"Forbidden environment variable '{var_name}' exposed to DEFENSE_DETECTOR role."
                )


@dataclass(frozen=True)
class BlindSamplePrediction:
    """Single sample prediction emitted by the blind defense detector."""

    sample_id: str
    malware_score: float
    signals: dict[str, float]
    fusion_score: float
    decision: str
    latency_ms: float

    def __post_init__(self) -> None:
        if not self.sample_id.strip():
            raise ValueError("sample_id must be non-empty.")
        if not math.isfinite(self.malware_score) or not math.isfinite(self.fusion_score):
            raise ValueError("malware_score and fusion_score must be finite floats.")
        if self.decision not in CANONICAL_DECISIONS:
            raise ValueError(
                f"Decision '{self.decision}' must be one of {sorted(CANONICAL_DECISIONS)}."
            )
        if not math.isfinite(self.latency_ms) or self.latency_ms < 0.0:
            raise ValueError("latency_ms must be a non-negative finite float.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "malware_score": self.malware_score,
            "signals": dict(sorted(self.signals.items())),
            "fusion_score": self.fusion_score,
            "decision": self.decision,
            "latency_ms": self.latency_ms,
        }


def _compute_prediction_package_sha256(
    *,
    run_id: str,
    experiment_code: str,
    config_hash: str,
    model_hash: str,
    view_map_hash: str,
    detector_config_hash: str,
    threshold_id: str,
    threshold_value: float,
    seed: int,
    predictions: Sequence[BlindSamplePrediction],
) -> str:
    payload = {
        "run_id": run_id,
        "experiment_code": experiment_code,
        "config_hash": config_hash,
        "model_hash": model_hash,
        "view_map_hash": view_map_hash,
        "detector_config_hash": detector_config_hash,
        "threshold_id": threshold_id,
        "threshold_value": threshold_value,
        "seed": seed,
        "predictions": [p.to_dict() for p in predictions],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class BlindPredictionPackage:
    """Cryptographically sealed prediction package emitted by DEFENSE_DETECTOR prior to scoring."""

    run_id: str
    experiment_code: str
    config_hash: str
    model_hash: str
    view_map_hash: str
    detector_config_hash: str
    threshold_id: str
    threshold_value: float
    seed: int
    predictions: tuple[BlindSamplePrediction, ...]
    package_sha256: str

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        experiment_code: str,
        config_hash: str,
        model_hash: str,
        view_map_hash: str,
        detector_config_hash: str,
        threshold_id: str,
        threshold_value: float,
        seed: int,
        predictions: Sequence[BlindSamplePrediction],
    ) -> BlindPredictionPackage:
        BlindCustodyGuard(role=EvaluationRole.DEFENSE_DETECTOR).assert_environment_clean()
        if len(predictions) == 0:
            raise ValueError("predictions cannot be empty.")
        validate_unique_sample_ids(
            [p.sample_id for p in predictions], context="BlindPredictionPackage"
        )
        preds_tuple = tuple(predictions)
        digest = _compute_prediction_package_sha256(
            run_id=run_id,
            experiment_code=experiment_code,
            config_hash=config_hash,
            model_hash=model_hash,
            view_map_hash=view_map_hash,
            detector_config_hash=detector_config_hash,
            threshold_id=threshold_id,
            threshold_value=threshold_value,
            seed=seed,
            predictions=preds_tuple,
        )
        return cls(
            run_id=run_id,
            experiment_code=experiment_code,
            config_hash=config_hash,
            model_hash=model_hash,
            view_map_hash=view_map_hash,
            detector_config_hash=detector_config_hash,
            threshold_id=threshold_id,
            threshold_value=threshold_value,
            seed=seed,
            predictions=preds_tuple,
            package_sha256=digest,
        )

    def verify_integrity(self) -> bool:
        expected = _compute_prediction_package_sha256(
            run_id=self.run_id,
            experiment_code=self.experiment_code,
            config_hash=self.config_hash,
            model_hash=self.model_hash,
            view_map_hash=self.view_map_hash,
            detector_config_hash=self.detector_config_hash,
            threshold_id=self.threshold_id,
            threshold_value=self.threshold_value,
            seed=self.seed,
            predictions=self.predictions,
        )
        if expected != self.package_sha256:
            raise BlindCustodyIntegrityError(
                f"BlindPredictionPackage checksum mismatch for run '{self.run_id}': "
                f"expected {self.package_sha256}, computed {expected}."
            )
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_code": self.experiment_code,
            "config_hash": self.config_hash,
            "model_hash": self.model_hash,
            "view_map_hash": self.view_map_hash,
            "detector_config_hash": self.detector_config_hash,
            "threshold_id": self.threshold_id,
            "threshold_value": self.threshold_value,
            "seed": self.seed,
            "predictions": [p.to_dict() for p in self.predictions],
            "package_sha256": self.package_sha256,
        }

    def save(self, path: Path) -> None:
        self.verify_integrity()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> BlindPredictionPackage:
        raw = json.loads(path.read_text(encoding="utf-8"))
        preds = tuple(
            BlindSamplePrediction(
                sample_id=str(item["sample_id"]),
                malware_score=float(item["malware_score"]),
                signals={str(k): float(v) for k, v in item["signals"].items()},
                fusion_score=float(item["fusion_score"]),
                decision=str(item["decision"]),
                latency_ms=float(item["latency_ms"]),
            )
            for item in raw["predictions"]
        )
        pkg = cls(
            run_id=str(raw["run_id"]),
            experiment_code=str(raw["experiment_code"]),
            config_hash=str(raw["config_hash"]),
            model_hash=str(raw["model_hash"]),
            view_map_hash=str(raw["view_map_hash"]),
            detector_config_hash=str(raw["detector_config_hash"]),
            threshold_id=str(raw["threshold_id"]),
            threshold_value=float(raw["threshold_value"]),
            seed=int(raw["seed"]),
            predictions=preds,
            package_sha256=str(raw["package_sha256"]),
        )
        pkg.verify_integrity()
        return pkg


def _compute_ground_truth_sha256(
    *,
    manifest_id: str,
    dataset_id: str,
    sample_ids: Sequence[str],
    labels: Sequence[int],
    is_malware: Sequence[int],
    clean_model_scores: Sequence[float] | None,
    poisoned_triggered_scores: Sequence[float] | None,
) -> str:
    payload = {
        "manifest_id": manifest_id,
        "dataset_id": dataset_id,
        "sample_ids": list(sample_ids),
        "labels": list(labels),
        "is_malware": list(is_malware),
        "clean_model_scores": list(clean_model_scores) if clean_model_scores is not None else None,
        "poisoned_triggered_scores": (
            list(poisoned_triggered_scores) if poisoned_triggered_scores is not None else None
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class BlindGroundTruthManifest:
    """Sealed ground-truth manifest held exclusively in EVALUATION_SCORING custody."""

    manifest_id: str
    dataset_id: str
    sample_ids: tuple[str, ...]
    labels: tuple[int, ...]
    is_malware: tuple[int, ...]
    clean_model_scores: tuple[float, ...] | None
    poisoned_triggered_scores: tuple[float, ...] | None
    manifest_sha256: str

    @classmethod
    def create(
        cls,
        *,
        manifest_id: str,
        dataset_id: str,
        sample_ids: Sequence[str],
        labels: Sequence[int],
        is_malware: Sequence[int],
        clean_model_scores: Sequence[float] | None = None,
        poisoned_triggered_scores: Sequence[float] | None = None,
    ) -> BlindGroundTruthManifest:
        if len(sample_ids) == 0:
            raise ValueError("sample_ids cannot be empty.")
        validate_unique_sample_ids(sample_ids, context="BlindGroundTruthManifest")
        if not (len(sample_ids) == len(labels) == len(is_malware)):
            raise ValueError("sample_ids, labels, and is_malware must have equal length.")
        for idx, lbl in enumerate(labels):
            if isinstance(lbl, bool) or not isinstance(lbl, int) or lbl not in (0, 1):
                raise ValueError(
                    f"labels[{idx}] must be a binary integer in {{0, 1}}, got {lbl!r}."
                )
        for idx, mw in enumerate(is_malware):
            if isinstance(mw, bool) or not isinstance(mw, int) or mw not in (0, 1):
                raise ValueError(
                    f"is_malware[{idx}] must be a binary integer in {{0, 1}}, got {mw!r}."
                )
        if clean_model_scores is not None:
            if len(clean_model_scores) != len(sample_ids):
                raise ValueError(
                    f"clean_model_scores length ({len(clean_model_scores)}) must match "
                    f"sample_ids length ({len(sample_ids)})."
                )
            for idx, sc in enumerate(clean_model_scores):
                if (
                    isinstance(sc, bool)
                    or not isinstance(sc, (int, float))
                    or not math.isfinite(float(sc))
                ):
                    raise ValueError(
                        f"clean_model_scores[{idx}] must be a finite float, got {sc!r}."
                    )
        if poisoned_triggered_scores is not None:
            if len(poisoned_triggered_scores) != len(sample_ids):
                raise ValueError(
                    f"poisoned_triggered_scores length ({len(poisoned_triggered_scores)}) "
                    f"must match sample_ids length ({len(sample_ids)})."
                )
            for idx, sc in enumerate(poisoned_triggered_scores):
                if (
                    isinstance(sc, bool)
                    or not isinstance(sc, (int, float))
                    or not math.isfinite(float(sc))
                ):
                    raise ValueError(
                        f"poisoned_triggered_scores[{idx}] must be a finite float, got {sc!r}."
                    )

        s_tuple = tuple(sample_ids)
        l_tuple = tuple(int(x) for x in labels)
        m_tuple = tuple(int(x) for x in is_malware)
        c_tuple = (
            tuple(float(x) for x in clean_model_scores) if clean_model_scores is not None else None
        )
        p_tuple = (
            tuple(float(x) for x in poisoned_triggered_scores)
            if poisoned_triggered_scores is not None
            else None
        )
        digest = _compute_ground_truth_sha256(
            manifest_id=manifest_id,
            dataset_id=dataset_id,
            sample_ids=s_tuple,
            labels=l_tuple,
            is_malware=m_tuple,
            clean_model_scores=c_tuple,
            poisoned_triggered_scores=p_tuple,
        )
        return cls(
            manifest_id=manifest_id,
            dataset_id=dataset_id,
            sample_ids=s_tuple,
            labels=l_tuple,
            is_malware=m_tuple,
            clean_model_scores=c_tuple,
            poisoned_triggered_scores=p_tuple,
            manifest_sha256=digest,
        )

    def verify_integrity(self) -> bool:
        expected = _compute_ground_truth_sha256(
            manifest_id=self.manifest_id,
            dataset_id=self.dataset_id,
            sample_ids=self.sample_ids,
            labels=self.labels,
            is_malware=self.is_malware,
            clean_model_scores=self.clean_model_scores,
            poisoned_triggered_scores=self.poisoned_triggered_scores,
        )
        if expected != self.manifest_sha256:
            raise BlindCustodyIntegrityError(
                f"BlindGroundTruthManifest checksum mismatch for '{self.manifest_id}'."
            )
        return True


@dataclass(frozen=True)
class BlindEvaluationReport:
    """Immutable report generated by joining sealed predictions with blind ground truth."""

    run_id: str
    experiment_code: str
    prediction_package_sha256: str
    ground_truth_sha256: str
    threshold_id: str
    locked_threshold: float
    auroc: float
    fpr: FPRResult
    recall: RecallResult
    asr: ASRResult | None
    latency: LatencySummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_code": self.experiment_code,
            "prediction_package_sha256": self.prediction_package_sha256,
            "ground_truth_sha256": self.ground_truth_sha256,
            "threshold_id": self.threshold_id,
            "locked_threshold": self.locked_threshold,
            "auroc": self.auroc,
            "fpr": self.fpr.to_dict(),
            "recall": self.recall.to_dict(),
            "asr": self.asr.to_dict() if self.asr is not None else None,
            "latency": self.latency.to_dict(),
        }


class BlindEvaluator:
    """Authorized evaluation scoring engine that joins sealed predictions with ground truth."""

    def __init__(self, role: EvaluationRole) -> None:
        if role != EvaluationRole.EVALUATION_SCORING:
            raise BlindRolePermissionError(
                f"Role '{role}' is forbidden from instantiating BlindEvaluator; "
                f"only '{EvaluationRole.EVALUATION_SCORING}' is authorized."
            )
        self.role = role

    def score_predictions(
        self,
        *,
        prediction_package: BlindPredictionPackage,
        ground_truth: BlindGroundTruthManifest,
        expected_locked_threshold: float,
    ) -> BlindEvaluationReport:
        prediction_package.verify_integrity()
        ground_truth.verify_integrity()

        if not math.isclose(
            prediction_package.threshold_value,
            expected_locked_threshold,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise PostHocTuningForbiddenError(
                f"Post-hoc threshold tuning detected: package threshold "
                f"({prediction_package.threshold_value}) != locked D1 threshold "
                f"({expected_locked_threshold})."
            )

        pred_map = {p.sample_id: p for p in prediction_package.predictions}
        truth_ids = list(ground_truth.sample_ids)
        if set(pred_map.keys()) != set(truth_ids):
            raise BlindCustodyIntegrityError(
                "Sample ID set mismatch between sealed prediction package and blind ground truth."
            )

        ordered_preds = [pred_map[sid] for sid in truth_ids]
        for p in ordered_preds:
            expected_positive = p.fusion_score >= prediction_package.threshold_value
            actual_positive = p.decision in POSITIVE_DETECTOR_DECISIONS
            if expected_positive != actual_positive:
                raise PostHocTuningForbiddenError(
                    f"Post-hoc decision manipulation detected on sample '{p.sample_id}': "
                    f"fusion_score={p.fusion_score}, decision={p.decision}, "
                    f"threshold={prediction_package.threshold_value}."
                )

        fusion_scores = [p.fusion_score for p in ordered_preds]
        decisions = [p.decision for p in ordered_preds]
        latencies = [p.latency_ms for p in ordered_preds]

        auroc_val = compute_auroc(
            ground_truth.labels,
            fusion_scores,
            sample_ids=truth_ids,
        )
        fpr_res = compute_fpr(
            ground_truth.labels,
            decisions,
            threshold=prediction_package.threshold_value,
            sample_ids=truth_ids,
        )
        recall_res = compute_recall(
            ground_truth.labels,
            decisions,
            threshold=prediction_package.threshold_value,
            sample_ids=truth_ids,
        )

        asr_res: ASRResult | None = None
        if (
            ground_truth.clean_model_scores is not None
            and ground_truth.poisoned_triggered_scores is not None
        ):
            asr_res = compute_asr(
                is_malware=ground_truth.is_malware,
                clean_model_scores=ground_truth.clean_model_scores,
                poisoned_triggered_scores=ground_truth.poisoned_triggered_scores,
                detector_decisions_or_scores=decisions,
                sample_ids=truth_ids,
            )

        latency_res = compute_latency_summary(latencies, scope="detector_only")

        return BlindEvaluationReport(
            run_id=prediction_package.run_id,
            experiment_code=prediction_package.experiment_code,
            prediction_package_sha256=prediction_package.package_sha256,
            ground_truth_sha256=ground_truth.manifest_sha256,
            threshold_id=prediction_package.threshold_id,
            locked_threshold=prediction_package.threshold_value,
            auroc=auroc_val,
            fpr=fpr_res,
            recall=recall_res,
            asr=asr_res,
            latency=latency_res,
        )
