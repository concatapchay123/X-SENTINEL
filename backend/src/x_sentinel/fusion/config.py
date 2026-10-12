from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class FusionConfigError(ValueError):
    """Raised when fusion or calibration configuration fails validation."""


@dataclass(frozen=True)
class FusionConfig:
    """Configuration for detector signal fusion."""

    strategy: str = "weighted_sum"
    version: str = "1.0.0"
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "m1": 0.20,
            "m2": 0.20,
            "m3": 0.20,
            "m4": 0.20,
            "m5": 0.20,
        }
    )
    bias: float = 0.0

    VALID_STRATEGIES = ("weighted_sum", "logistic_regression", "max_signal", "demo_mean")
    REQUIRED_SIGNALS = ("m1", "m2", "m3", "m4", "m5")

    def __post_init__(self) -> None:
        if self.strategy not in self.VALID_STRATEGIES:
            raise FusionConfigError(
                f"Unsupported fusion strategy '{self.strategy}'. "
                f"Valid options: {self.VALID_STRATEGIES}."
            )

        if self.strategy in ("weighted_sum", "logistic_regression"):
            if not isinstance(self.weights, dict):
                raise FusionConfigError(
                    "Fusion weights must be a dictionary mapping signal names to floats."
                )
            for sig in self.REQUIRED_SIGNALS:
                if sig not in self.weights:
                    raise FusionConfigError(f"Missing weight for required signal '{sig}'.")
                w_val = float(self.weights[sig])
                if self.strategy == "weighted_sum" and w_val < 0.0:
                    raise FusionConfigError(
                        f"Weight for signal '{sig}' must be non-negative, got {w_val}."
                    )

            if self.strategy == "weighted_sum":
                total_weight = sum(float(self.weights[s]) for s in self.REQUIRED_SIGNALS)
                if abs(total_weight - 1.0) > 1e-5:
                    raise FusionConfigError(
                        f"Weighted sum weights must sum to 1.0 (got {total_weight:.6f})."
                    )


@dataclass(frozen=True)
class CalibrationConfig:
    """Configuration for decision threshold calibration (D0/D1)."""

    mode: str = "d0"
    d0_threshold: float = 0.50
    d1_threshold: float | None = None
    fpr_target: float = 0.01
    d1_artifact_path: str | None = None
    quarantine_threshold: float = 0.85

    VALID_MODES = ("d0", "d1")

    def __post_init__(self) -> None:
        if self.mode not in self.VALID_MODES:
            raise FusionConfigError(
                f"Unsupported calibration mode '{self.mode}'. Valid options: {self.VALID_MODES}."
            )
        if not (0.0 <= self.d0_threshold <= 1.0):
            raise FusionConfigError(f"d0_threshold must be in [0.0, 1.0], got {self.d0_threshold}.")
        if self.d1_threshold is not None and not (0.0 <= self.d1_threshold <= 1.0):
            raise FusionConfigError(f"d1_threshold must be in [0.0, 1.0], got {self.d1_threshold}.")
        if not (0.0 < self.fpr_target < 1.0):
            raise FusionConfigError(
                f"fpr_target must be strictly in (0.0, 1.0), got {self.fpr_target}."
            )
        if not (0.0 <= self.quarantine_threshold <= 1.0):
            raise FusionConfigError(
                f"quarantine_threshold must be in [0.0, 1.0], got {self.quarantine_threshold}."
            )
        active_thresh = (
            self.d1_threshold
            if self.mode == "d1" and self.d1_threshold is not None
            else self.d0_threshold
        )
        if self.quarantine_threshold < active_thresh:
            raise FusionConfigError(
                f"quarantine_threshold ({self.quarantine_threshold}) cannot be lower than "
                f"alert threshold ({active_thresh})."
            )


@dataclass(frozen=True)
class FusionLayerConfig:
    """Unified configuration for the Fusion, Calibration, and Decision layer."""

    status: str
    version: str
    fusion: FusionConfig
    calibration: CalibrationConfig
    raw_config: dict[str, Any] = field(default_factory=dict)


def load_fusion_config(
    config_source: Path | str | Mapping[str, Any] | None = None,
) -> FusionLayerConfig:
    """Load and validate fusion and calibration configuration from YAML file or mapping."""
    if config_source is None:
        config_path = Path("configs/detector.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    elif isinstance(config_source, (str, Path)):
        config_path = Path(config_source)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    elif isinstance(config_source, Mapping):
        data = dict(config_source)
    else:
        raise TypeError(f"Invalid config_source type: {type(config_source)}")

    if not isinstance(data, dict):
        raise FusionConfigError("Configuration must be a mapping/dictionary.")

    status = str(data.get("status", "PARTIAL_BASELINE"))
    version = str(data.get("version", "1.0.0"))

    # Parse fusion subsection
    fusion_raw = data.get("fusion") or {}
    if not isinstance(fusion_raw, dict):
        raise FusionConfigError("The 'fusion' section must be a dictionary.")

    strategy = fusion_raw.get("strategy")
    if strategy is None:
        strategy = "weighted_sum"

    weights_raw = fusion_raw.get("weights")
    if weights_raw is None:
        weights = {
            "m1": 0.20,
            "m2": 0.20,
            "m3": 0.20,
            "m4": 0.20,
            "m5": 0.20,
        }
    else:
        weights = {str(k).lower(): float(v) for k, v in weights_raw.items()}

    bias = float(fusion_raw.get("bias", 0.0))
    fusion_cfg = FusionConfig(
        strategy=str(strategy),
        version=str(fusion_raw.get("version", version)),
        weights=weights,
        bias=bias,
    )

    # Parse calibration subsection
    calib_raw = data.get("calibration") or {}
    if not isinstance(calib_raw, dict):
        raise FusionConfigError("The 'calibration' section must be a dictionary.")

    mode = str(calib_raw.get("mode", "d0")).lower()
    d0_threshold = float(calib_raw.get("d0_threshold", 0.50))
    d1_thresh_val = calib_raw.get("d1_threshold")
    d1_threshold = float(d1_thresh_val) if d1_thresh_val is not None else None
    fpr_target = float(calib_raw.get("fpr_target", 0.01))
    d1_artifact = calib_raw.get("d1_artifact_path")
    quarantine_thresh = float(calib_raw.get("quarantine_threshold", 0.85))

    calib_cfg = CalibrationConfig(
        mode=mode,
        d0_threshold=d0_threshold,
        d1_threshold=d1_threshold,
        fpr_target=fpr_target,
        d1_artifact_path=str(d1_artifact) if d1_artifact else None,
        quarantine_threshold=quarantine_thresh,
    )

    return FusionLayerConfig(
        status=status,
        version=version,
        fusion=fusion_cfg,
        calibration=calib_cfg,
        raw_config=data,
    )


def compute_fusion_config_hash(config_source: Path | str | Mapping[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of configuration content."""
    if isinstance(config_source, (str, Path)):
        path = Path(config_source)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        raw_bytes = path.read_bytes()
        return hashlib.sha256(raw_bytes).hexdigest()
    elif isinstance(config_source, Mapping):
        serialized = json.dumps(dict(config_source), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    else:
        raise TypeError(f"Invalid config_source type: {type(config_source)}")
