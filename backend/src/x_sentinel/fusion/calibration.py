from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from x_sentinel.fusion.config import CalibrationConfig


class CalibrationError(ValueError):
    """Base exception for calibration failures."""


class CalibrationIntegrityError(CalibrationError):
    """Raised when a calibration artifact checksum or content fails verification."""


class CalibrationUnresolvedError(RuntimeError):
    """Raised when scientific mode requires a calibrated threshold that is not yet frozen."""


class InsufficientDataError(CalibrationError):
    """Raised when insufficient calibration samples are provided."""


def wilson_score_interval(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion.

    Formula:
        (p_hat + z^2 / (2n) +/- z * sqrt((p_hat * (1 - p_hat) / n) + (z^2 / (4n^2))))
        divided by (1 + z^2 / n)

    Args:
        successes: Number of positive outcomes (e.g., false positives).
        trials: Total number of trials (e.g., benign calibration samples).
        confidence: Confidence level (default: 0.95).

    Returns:
        tuple[float, float]: (lower_bound, upper_bound) clipped to [0.0, 1.0].
    """
    if trials <= 0:
        raise ValueError(f"trials must be strictly positive, got {trials}.")
    if not (0 <= successes <= trials):
        raise ValueError(f"successes must be in [0, {trials}], got {successes}.")

    # Standard normal quantiles for common confidence levels
    if abs(confidence - 0.95) < 1e-4:
        z = 1.959963984540054
    elif abs(confidence - 0.99) < 1e-4:
        z = 2.5758293035489004
    elif abs(confidence - 0.90) < 1e-4:
        z = 1.6448536269514722
    else:
        # Approximate standard normal quantile
        # using rational approximation or inverse error function
        from scipy.stats import norm

        z = float(norm.ppf(1.0 - (1.0 - confidence) / 2.0))

    n = float(trials)
    p_hat = float(successes) / n
    z2 = z * z

    denominator = 1.0 + (z2 / n)
    center = (p_hat + (z2 / (2.0 * n))) / denominator

    variance_term = (p_hat * (1.0 - p_hat) / n) + (z2 / (4.0 * n * n))
    half_width = (z * math.sqrt(max(0.0, variance_term))) / denominator

    lower = max(0.0, center - half_width)
    upper = min(1.0, center + half_width)
    if successes == 0:
        lower = 0.0
    if successes == trials:
        upper = 1.0
    return float(lower), float(upper)


@dataclass(frozen=True)
class CalibrationArtifact:
    """Immutable calibration record storing frozen threshold provenance."""

    artifact_id: str
    version: str
    mode: str
    target_fpr: float
    threshold: float
    sample_count: int
    empirical_fpr: float
    wilson_ci_low: float
    wilson_ci_high: float
    dataset_hash: str
    created_at: str
    payload_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def save(self, destination: Path | str) -> Path:
        target_path = Path(destination)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(self.to_json(), encoding="utf-8")
        return target_path

    @classmethod
    def load(cls, source_path: Path | str) -> CalibrationArtifact:
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Calibration artifact not found at {path}")

        try:
            raw_content = path.read_text(encoding="utf-8")
            data = json.loads(raw_content)
        except Exception as exc:
            raise CalibrationIntegrityError(
                f"Corrupted calibration artifact at {path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise CalibrationIntegrityError("Calibration artifact JSON must be an object.")

        required_keys = (
            "artifact_id",
            "version",
            "mode",
            "target_fpr",
            "threshold",
            "sample_count",
            "empirical_fpr",
            "wilson_ci_low",
            "wilson_ci_high",
            "dataset_hash",
            "created_at",
            "payload_sha256",
        )
        for k in required_keys:
            if k not in data:
                raise CalibrationIntegrityError(
                    f"Missing required key '{k}' in calibration artifact."
                )

        expected_hash = data["payload_sha256"]
        canonical_payload = {k: data[k] for k in sorted(data.keys()) if k != "payload_sha256"}
        computed_hash = hashlib.sha256(
            json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        if computed_hash != expected_hash:
            raise CalibrationIntegrityError(
                f"Calibration artifact checksum mismatch. Expected {expected_hash}, "
                f"computed {computed_hash}."
            )

        return cls(
            artifact_id=str(data["artifact_id"]),
            version=str(data["version"]),
            mode=str(data["mode"]),
            target_fpr=float(data["target_fpr"]),
            threshold=float(data["threshold"]),
            sample_count=int(data["sample_count"]),
            empirical_fpr=float(data["empirical_fpr"]),
            wilson_ci_low=float(data["wilson_ci_low"]),
            wilson_ci_high=float(data["wilson_ci_high"]),
            dataset_hash=str(data["dataset_hash"]),
            created_at=str(data["created_at"]),
            payload_sha256=str(data["payload_sha256"]),
        )


class D1Calibration:
    """Protocol for D1 Calibration using a trusted benign validation set."""

    @staticmethod
    def fit(
        benign_scores: Sequence[float],
        target_fpr: float = 0.01,
        dataset_hash: str | None = None,
        artifact_id: str | None = None,
        version: str = "1.0.0",
    ) -> CalibrationArtifact:
        """Fit empirical threshold on benign calibration scores targeting FPR <= target_fpr."""
        if not benign_scores:
            raise InsufficientDataError("Benign score collection cannot be empty.")
        if len(benign_scores) < 10:
            raise InsufficientDataError(
                f"At least 10 benign samples required for calibration, got {len(benign_scores)}."
            )
        if not (0.0 < target_fpr < 1.0):
            raise CalibrationError(f"target_fpr must be in (0, 1), got {target_fpr}.")

        validated: list[float] = []
        for i, val in enumerate(benign_scores):
            try:
                f_val = float(val)
            except (TypeError, ValueError) as exc:
                raise CalibrationError(f"Non-numeric score at index {i}: {val}") from exc
            if not math.isfinite(f_val):
                raise CalibrationError(f"Non-finite score at index {i}: {f_val}")
            if not (0.0 <= f_val <= 1.0):
                raise CalibrationError(f"Score out of domain [0, 1] at index {i}: {f_val}")
            validated.append(f_val)

        n = len(validated)
        sorted_scores = sorted(validated)

        # To guarantee empirical FPR <= target_fpr:
        # We select the threshold as the (1 - target_fpr) empirical quantile
        # Rank k (1-indexed) such that at most floor(target_fpr * n) scores are >= threshold
        allowed_fps = int(math.floor(target_fpr * n))
        rank_index = n - allowed_fps
        # Ensure index is within [0, n - 1]
        threshold_idx = min(max(0, rank_index), n - 1)
        threshold = sorted_scores[threshold_idx]

        # Calculate actual empirical false positives at this threshold
        actual_fps = sum(1 for s in sorted_scores if s >= threshold)
        empirical_fpr = float(actual_fps) / float(n)

        # Wilson 95% confidence interval
        ci_low, ci_high = wilson_score_interval(actual_fps, n, confidence=0.95)

        if dataset_hash is None:
            # Deterministic hash of input scores
            score_bytes = json.dumps(sorted_scores, separators=(",", ":")).encode("utf-8")
            computed_dataset_hash = hashlib.sha256(score_bytes).hexdigest()
        else:
            computed_dataset_hash = dataset_hash

        art_id = artifact_id or f"calib-d1-{computed_dataset_hash[:12]}"
        now_iso = datetime.now(UTC).isoformat()

        payload = {
            "artifact_id": art_id,
            "created_at": now_iso,
            "dataset_hash": computed_dataset_hash,
            "empirical_fpr": empirical_fpr,
            "mode": "d1",
            "sample_count": n,
            "target_fpr": target_fpr,
            "threshold": threshold,
            "version": version,
            "wilson_ci_high": ci_high,
            "wilson_ci_low": ci_low,
        }
        payload_sha256 = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        return CalibrationArtifact(
            artifact_id=art_id,
            version=version,
            mode="d1",
            target_fpr=target_fpr,
            threshold=threshold,
            sample_count=n,
            empirical_fpr=empirical_fpr,
            wilson_ci_low=ci_low,
            wilson_ci_high=ci_high,
            dataset_hash=computed_dataset_hash,
            created_at=now_iso,
            payload_sha256=payload_sha256,
        )


class D0Calibration:
    """Protocol for D0 Alert Budget Mode (no trusted reference)."""

    @staticmethod
    def get_threshold(default_threshold: float = 0.50) -> float:
        if not (0.0 <= default_threshold <= 1.0):
            raise CalibrationError(f"D0 threshold must be in [0.0, 1.0], got {default_threshold}.")
        return float(default_threshold)


class CalibrationEngine:
    """Orchestrates threshold calibration lookup and enforcement under D0/D1 policies."""

    def __init__(self, config: CalibrationConfig, demo_mode: bool = True) -> None:
        self.config = config
        self.demo_mode = demo_mode
        self._artifact: CalibrationArtifact | None = None
        self._resolved_threshold: float | None = None

        self._initialize_threshold()

    def _initialize_threshold(self) -> None:
        if self.config.mode == "d0":
            self._resolved_threshold = self.config.d0_threshold
        elif self.config.mode == "d1":
            if self.config.d1_threshold is not None:
                self._resolved_threshold = self.config.d1_threshold
            elif self.config.d1_artifact_path is not None:
                artifact_path = Path(self.config.d1_artifact_path)
                if artifact_path.exists():
                    self._artifact = CalibrationArtifact.load(artifact_path)
                    self._resolved_threshold = self._artifact.threshold
                else:
                    if not self.demo_mode:
                        raise CalibrationUnresolvedError(
                            f"Scientific D1 calibration artifact missing at {artifact_path}."
                        )
                    self._resolved_threshold = None
            else:
                if not self.demo_mode:
                    raise CalibrationUnresolvedError(
                        "Scientific D1 mode requires frozen d1_threshold or d1_artifact_path."
                    )
                self._resolved_threshold = None

    @property
    def active_threshold(self) -> float | None:
        return self._resolved_threshold

    @property
    def quarantine_threshold(self) -> float:
        return self.config.quarantine_threshold

    @property
    def artifact(self) -> CalibrationArtifact | None:
        return self._artifact

    def resolve(self) -> float:
        """Return the active threshold, or fail closed in scientific mode."""
        if self._resolved_threshold is not None:
            return self._resolved_threshold
        if self.demo_mode:
            # Fall back to D0 threshold in demo mode with warning
            return self.config.d0_threshold
        raise CalibrationUnresolvedError(
            f"Threshold unresolved under calibration mode '{self.config.mode}'."
        )
