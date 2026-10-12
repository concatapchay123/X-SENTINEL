from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class M1Config:
    enabled: bool = True
    formula: str = "tadr"
    eps: float = 1e-12

    def __post_init__(self) -> None:
        if self.formula != "tadr":
            raise ValueError(f"Unsupported M1 formula: {self.formula}. Expected 'tadr'.")
        if self.eps <= 0.0:
            raise ValueError(f"M1 eps must be positive, got {self.eps}.")


@dataclass(frozen=True)
class M2Config:
    enabled: bool = True
    formula: str = "tabular_strip"
    n_mix: int = 16
    alpha: float = 0.2
    sampling_seed: int = 42
    invert_entropy: bool = True

    def __post_init__(self) -> None:
        if self.formula != "tabular_strip":
            raise ValueError(f"Unsupported M2 formula: {self.formula}. Expected 'tabular_strip'.")
        if self.n_mix < 1:
            raise ValueError(f"M2 n_mix must be >= 1, got {self.n_mix}.")
        if not (0.0 < self.alpha < 1.0):
            raise ValueError(f"M2 alpha must be strictly in (0, 1), got {self.alpha}.")


@dataclass(frozen=True)
class M3Config:
    enabled: bool = True
    aggregation: str = "absolute_shap_sum_by_view"
    metric: str = "max_concentration"
    eps: float = 1e-12

    def __post_init__(self) -> None:
        if self.aggregation != "absolute_shap_sum_by_view":
            raise ValueError(
                f"Unsupported M3 aggregation: {self.aggregation}. Expected 'absolute_shap_sum_by_view'."
            )
        if self.eps <= 0.0:
            raise ValueError(f"M3 eps must be positive, got {self.eps}.")


@dataclass(frozen=True)
class M4Config:
    enabled: bool = True
    strategy: str = "symmetric_disagreement"
    ablation_strategies: list[str] = field(
        default_factory=lambda: [
            "view_std",
            "behavioral_metadata_gap",
            "full_vs_behavioral_gap",
            "max_pairwise_difference",
        ]
    )

    VALID_STRATEGIES = (
        "symmetric_disagreement",
        "view_std",
        "behavioral_metadata_gap",
        "full_vs_behavioral_gap",
        "max_pairwise_difference",
    )

    def __post_init__(self) -> None:
        if self.strategy not in self.VALID_STRATEGIES:
            raise ValueError(
                f"Unsupported M4 strategy '{self.strategy}'. Valid options: {self.VALID_STRATEGIES}."
            )


@dataclass(frozen=True)
class M5Config:
    enabled: bool = True
    rules_file: str = "configs/m5_rules.json"
    rules_sha256: str = "2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d"
    metric: str = "plausibility"

    def __post_init__(self) -> None:
        if self.enabled:
            if not self.rules_file:
                raise ValueError("M5 rules_file cannot be empty when enabled.")
            if not self.rules_sha256 or len(self.rules_sha256) != 64:
                raise ValueError("M5 rules_sha256 must be a valid 64-character SHA-256 hash.")


@dataclass(frozen=True)
class DetectorConfig:
    status: str
    version: str
    m1: M1Config
    m2: M2Config
    m3: M3Config
    m4: M4Config
    m5: M5Config
    raw_config: dict[str, Any] = field(default_factory=dict)


def load_detector_config(config_source: Path | str | dict[str, Any] | None = None) -> DetectorConfig:
    if config_source is None:
        config_path = Path("configs/detector.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"Detector config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    elif isinstance(config_source, (str, Path)):
        config_path = Path(config_source)
        if not config_path.exists():
            raise FileNotFoundError(f"Detector config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    elif isinstance(config_source, dict):
        data = config_source
    else:
        raise TypeError(f"Invalid config_source type: {type(config_source)}")

    if not isinstance(data, dict):
        raise ValueError("Detector configuration must be a mapping/dictionary.")

    status = str(data.get("status", "UNKNOWN"))
    version = str(data.get("version", "1.0.0"))

    m1_data = data.get("m1", {}) or {}
    m1_cfg = M1Config(
        enabled=bool(m1_data.get("enabled", True)),
        formula=str(m1_data.get("formula", "tadr")),
        eps=float(m1_data.get("eps", 1e-12)),
    )

    m2_data = data.get("m2", {}) or {}
    m2_cfg = M2Config(
        enabled=bool(m2_data.get("enabled", True)),
        formula=str(m2_data.get("formula", "tabular_strip")),
        n_mix=int(m2_data.get("n_mix", 16) if m2_data.get("n_mix") is not None else 16),
        alpha=float(m2_data.get("alpha", 0.2) if m2_data.get("alpha") is not None else 0.2),
        sampling_seed=int(
            m2_data.get("sampling_seed", 42) if m2_data.get("sampling_seed") is not None else 42
        ),
        invert_entropy=bool(m2_data.get("invert_entropy", True)),
    )

    m3_data = data.get("m3", {}) or {}
    m3_cfg = M3Config(
        enabled=bool(m3_data.get("enabled", True)),
        aggregation=str(m3_data.get("aggregation", "absolute_shap_sum_by_view")),
        metric=str(m3_data.get("metric", "max_concentration")),
        eps=float(m3_data.get("eps", 1e-12)),
    )

    m4_data = data.get("m4", {}) or {}
    strategy = m4_data.get("strategy")
    if strategy is None:
        strategy = "symmetric_disagreement"
    m4_cfg = M4Config(
        enabled=bool(m4_data.get("enabled", True)),
        strategy=str(strategy),
        ablation_strategies=list(
            m4_data.get(
                "ablation_strategies",
                [
                    "view_std",
                    "behavioral_metadata_gap",
                    "full_vs_behavioral_gap",
                    "max_pairwise_difference",
                ],
            )
        ),
    )

    m5_data = data.get("m5", {}) or {}
    rules_file = m5_data.get("rules_file") or "configs/m5_rules.json"
    rules_sha256 = (
        m5_data.get("rules_sha256")
        or "2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d"
    )
    m5_cfg = M5Config(
        enabled=bool(m5_data.get("enabled", True)),
        rules_file=str(rules_file),
        rules_sha256=str(rules_sha256),
        metric=str(m5_data.get("metric", "plausibility")),
    )

    return DetectorConfig(
        status=status,
        version=version,
        m1=m1_cfg,
        m2=m2_cfg,
        m3=m3_cfg,
        m4=m4_cfg,
        m5=m5_cfg,
        raw_config=data,
    )


def compute_detector_config_hash(config_path: Path | str) -> str:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    raw_bytes = path.read_bytes()
    return hashlib.sha256(raw_bytes).hexdigest()
