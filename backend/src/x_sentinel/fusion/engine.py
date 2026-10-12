from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from x_sentinel.fusion.config import FusionConfig


class FusionError(ValueError):
    """Base exception for fusion failures."""


class MissingSignalError(FusionError):
    """Raised when one or more required M1-M5 signals are missing."""


class InvalidSignalError(FusionError):
    """Raised when signal values are non-numeric or non-finite."""


class SignalDomainError(FusionError):
    """Raised when signal values violate the expected [0.0, 1.0] mathematical domain."""


REQUIRED_SIGNALS = ("m1", "m2", "m3", "m4", "m5")


def validate_signals(signals: Mapping[str, Any] | Sequence[float]) -> dict[str, float]:
    """Validate and normalize detector signals into a clean dictionary.

    Args:
        signals: Mapping containing 'm1'..'m5' (floats or SignalResult),
                 or a sequence of 5 floats corresponding to [m1, m2, m3, m4, m5].

    Returns:
        dict[str, float] with keys 'm1', 'm2', 'm3', 'm4', 'm5', strictly in [0.0, 1.0].
    """
    clean_dict: dict[str, float] = {}

    if isinstance(signals, Mapping):
        # Case-insensitive mapping lookup
        normalized_keys = {str(k).strip().lower(): v for k, v in signals.items()}
        for sig in REQUIRED_SIGNALS:
            if sig not in normalized_keys:
                raise MissingSignalError(
                    f"Required detector signal '{sig}' is missing from input signals."
                )
            val = normalized_keys[sig]
            # Support SignalResult objects
            if hasattr(val, "score"):
                val = val.score
            try:
                f_val = float(val)
            except (TypeError, ValueError) as exc:
                raise InvalidSignalError(
                    f"Signal '{sig}' value '{val}' cannot be converted to float."
                ) from exc

            if not math.isfinite(f_val):
                raise InvalidSignalError(f"Signal '{sig}' is non-finite: {f_val}.")
            if not (0.0 <= f_val <= 1.0):
                raise SignalDomainError(f"Signal '{sig}' value {f_val} violates domain [0.0, 1.0].")
            clean_dict[sig] = f_val

    elif isinstance(signals, Sequence):
        if len(signals) != len(REQUIRED_SIGNALS):
            raise MissingSignalError(
                f"Expected exactly {len(REQUIRED_SIGNALS)} signals for sequence input, "
                f"got {len(signals)}."
            )
        for sig, val in zip(REQUIRED_SIGNALS, signals, strict=True):
            if hasattr(val, "score"):
                val = val.score
            try:
                f_val = float(val)
            except (TypeError, ValueError) as exc:
                raise InvalidSignalError(
                    f"Signal '{sig}' value '{val}' cannot be converted to float."
                ) from exc
            if not math.isfinite(f_val):
                raise InvalidSignalError(f"Signal '{sig}' is non-finite: {f_val}.")
            if not (0.0 <= f_val <= 1.0):
                raise SignalDomainError(f"Signal '{sig}' value {f_val} violates domain [0.0, 1.0].")
            clean_dict[sig] = f_val
    else:
        raise TypeError(f"signals must be a Mapping or Sequence, got {type(signals)}.")

    return clean_dict


@dataclass(frozen=True)
class FusionResult:
    """Immutable result of signal fusion calculation."""

    score: float
    strategy: str
    weights: dict[str, float] | None
    version: str
    signals: dict[str, float]
    diagnostics: dict[str, Any] = field(default_factory=dict)


class BaseFusionStrategy(ABC):
    """Abstract base class for all signal fusion algorithms."""

    @abstractmethod
    def fuse(self, signals: dict[str, float]) -> float:
        """Combine validated signals into a single scalar suspicion score."""


class WeightedSumFusion(BaseFusionStrategy):
    """Canonical convex combination of M1-M5 detector signals."""

    def __init__(self, weights: dict[str, float]) -> None:
        self.weights = {k: float(v) for k, v in weights.items()}

    def fuse(self, signals: dict[str, float]) -> float:
        score = sum(self.weights[k] * signals[k] for k in REQUIRED_SIGNALS)
        # Ensure numerical precision clamping to [0.0, 1.0]
        return min(max(float(score), 0.0), 1.0)


class LogisticRegressionFusion(BaseFusionStrategy):
    """Calibrated logistic regression fusion using weighted sum and bias."""

    def __init__(self, weights: dict[str, float], bias: float = 0.0) -> None:
        self.weights = {k: float(v) for k, v in weights.items()}
        self.bias = float(bias)

    def fuse(self, signals: dict[str, float]) -> float:
        z = self.bias + sum(self.weights[k] * signals[k] for k in REQUIRED_SIGNALS)
        # Numerically stable sigmoid
        if z >= 0:
            exp_neg_z = math.exp(-z)
            prob = 1.0 / (1.0 + exp_neg_z)
        else:
            exp_z = math.exp(z)
            prob = exp_z / (1.0 + exp_z)
        return min(max(float(prob), 0.0), 1.0)


class MaxSignalFusion(BaseFusionStrategy):
    """Worst-case anomaly fusion taking the maximum signal score."""

    def fuse(self, signals: dict[str, float]) -> float:
        return float(max(signals[k] for k in REQUIRED_SIGNALS))


class DemoMeanFusion(BaseFusionStrategy):
    """Unweighted arithmetic mean of signals."""

    def fuse(self, signals: dict[str, float]) -> float:
        return float(sum(signals.values()) / len(signals))


def demo_fusion(signals: dict[str, float]) -> float:
    """DEMO ONLY. Equal mean of available finite signals; never scientific evidence."""
    values = [float(v) for v in signals.values()]
    if not values:
        return 0.0
    return sum(values) / len(values)


class ScientificFusion:
    """Scientific fusion engine enforcing mathematical fidelity and versioned provenance."""

    def __init__(self, config: FusionConfig | None = None) -> None:
        self.config = config or FusionConfig()
        self.strategy_impl = self._create_strategy(self.config)

    def _create_strategy(self, config: FusionConfig) -> BaseFusionStrategy:
        if config.strategy == "weighted_sum":
            return WeightedSumFusion(config.weights)
        elif config.strategy == "logistic_regression":
            return LogisticRegressionFusion(config.weights, bias=config.bias)
        elif config.strategy == "max_signal":
            return MaxSignalFusion()
        elif config.strategy == "demo_mean":
            return DemoMeanFusion()
        else:
            raise FusionError(f"Unsupported fusion strategy '{config.strategy}'.")

    def score(self, signals: Mapping[str, Any] | Sequence[float]) -> float:
        """Validate input signals and compute calibrated suspicion score."""
        clean_signals = validate_signals(signals)
        return self.strategy_impl.fuse(clean_signals)

    def evaluate(self, signals: Mapping[str, Any] | Sequence[float]) -> FusionResult:
        """Validate signals and return detailed FusionResult with metadata."""
        clean_signals = validate_signals(signals)
        score = self.strategy_impl.fuse(clean_signals)
        return FusionResult(
            score=score,
            strategy=self.config.strategy,
            weights=self.config.weights
            if self.config.strategy in ("weighted_sum", "logistic_regression")
            else None,
            version=self.config.version,
            signals=clean_signals,
            diagnostics={
                "strategy": self.config.strategy,
                "bias": self.config.bias if self.config.strategy == "logistic_regression" else None,
            },
        )


class FusionEngine:
    """Facade orchestrating signal validation, fusion strategy calculation, and diagnostics."""

    def __init__(self, config: FusionConfig | None = None) -> None:
        self.config = config or FusionConfig()
        self._scientific = ScientificFusion(self.config)

    def evaluate(self, signals: Mapping[str, Any] | Sequence[float]) -> FusionResult:
        return self._scientific.evaluate(signals)

    def score(self, signals: Mapping[str, Any] | Sequence[float]) -> float:
        return self._scientific.score(signals)
