from __future__ import annotations

import math
import random
from typing import Any, Callable, Sequence

from x_sentinel.detection.config import M2Config
from x_sentinel.domain import SignalResult


def binary_entropy(p: float, eps: float = 1e-12) -> float:
    """Compute binary Shannon entropy in bits for probability p in [0, 1].

    Formula:
        H(p) = - p * log2(p) - (1 - p) * log2(1 - p)
    Bounded in [0.0, 1.0].
    """
    if not isinstance(p, (int, float)) or isinstance(p, bool):
        raise TypeError(f"Probability must be numeric, got {type(p)}")
    val = float(p)
    if not math.isfinite(val):
        raise ValueError(f"Probability must be finite, got {val}")

    if val <= 0.0 or val >= 1.0:
        return 0.0

    p_clamped = min(max(val, eps), 1.0 - eps)
    term1 = p_clamped * math.log2(p_clamped)
    term2 = (1.0 - p_clamped) * math.log2(1.0 - p_clamped)
    entropy = -(term1 + term2)
    return float(min(max(entropy, 0.0), 1.0))


def tabular_strip(
    vector: Sequence[float],
    model_fn: Callable[[list[float]], float | tuple[float, Any]],
    benign_pool: Sequence[Sequence[float]],
    n_mix: int = 16,
    alpha: float = 0.2,
    sampling_seed: int = 42,
    invert_entropy: bool = True,
) -> tuple[float, dict[str, Any]]:
    """Tabular STRIP (STRong Intentional Perturbation adapted for tabular features).

    Perturbs input vector with N benign reference vectors drawn from pool:
        x_perturbed = (1 - alpha) * x + alpha * x_benign
    Evaluates model prediction probability on each perturbed vector, computes
    binary Shannon entropy across perturbations, and calculates average entropy.

    Returns:
        (score, diagnostics_dict)
    """
    if len(vector) == 0:
        raise ValueError("Input vector cannot be empty.")
    if len(benign_pool) == 0:
        raise ValueError("Benign reference pool cannot be empty.")
    if n_mix < 1:
        raise ValueError(f"n_mix must be >= 1, got {n_mix}.")
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha must be strictly in (0, 1), got {alpha}.")

    # Validate vector finiteness
    clean_vec = [float(v) for v in vector]
    for idx, val in enumerate(clean_vec):
        if not math.isfinite(val):
            raise ValueError(f"Vector contains non-finite value at index {idx}: {val}")

    dim = len(clean_vec)
    rng = random.Random(sampling_seed)
    pool_list = list(benign_pool)

    predictions: list[float] = []
    entropies: list[float] = []

    for _ in range(n_mix):
        benign_sample = rng.choice(pool_list)
        if len(benign_sample) != dim:
            raise ValueError(
                f"Dimension mismatch in benign pool sample: expected {dim}, got {len(benign_sample)}"
            )

        # Convex mixing: (1 - alpha) * x + alpha * x_benign
        mixed = [(1.0 - alpha) * clean_vec[i] + alpha * float(benign_sample[i]) for i in range(dim)]

        pred_raw = model_fn(mixed)
        if hasattr(pred_raw, "score"):
            pred_score = float(pred_raw.score)
        elif isinstance(pred_raw, (tuple, list)):
            pred_score = float(pred_raw[0])
        else:
            pred_score = float(pred_raw)

        # Clip probability to [0.0, 1.0]
        prob = min(max(pred_score, 0.0), 1.0)
        h = binary_entropy(prob)

        predictions.append(prob)
        entropies.append(h)

    avg_entropy = sum(entropies) / len(entropies)
    p_mean = sum(predictions) / len(predictions)
    variance = sum((p - p_mean) ** 2 for p in predictions) / len(predictions)
    p_std = math.sqrt(variance)

    score = (1.0 - avg_entropy) if invert_entropy else avg_entropy
    score_clamped = float(min(max(score, 0.0), 1.0))

    diagnostics: dict[str, Any] = {
        "formula": "tabular_strip",
        "n_mix": n_mix,
        "alpha": alpha,
        "sampling_seed": sampling_seed,
        "average_entropy": float(avg_entropy),
        "invert_entropy": invert_entropy,
        "p_mean": float(p_mean),
        "p_std": float(p_std),
        "prediction_min": float(min(predictions)),
        "prediction_max": float(max(predictions)),
    }

    return score_clamped, diagnostics


class M2StripDetector:
    """Tabular STRIP Detector implementing inference-time perturbation defense."""

    name: str = "m2"

    def __init__(
        self,
        config: M2Config | dict[str, Any] | None = None,
        benign_pool: Sequence[Sequence[float]] | None = None,
        model_service: Any = None,
    ) -> None:
        if config is None:
            self.config = M2Config()
        elif isinstance(config, M2Config):
            self.config = config
        elif isinstance(config, dict):
            self.config = M2Config(
                enabled=bool(config.get("enabled", True)),
                formula=str(config.get("formula", "tabular_strip")),
                n_mix=int(config.get("n_mix", 16) if config.get("n_mix") is not None else 16),
                alpha=float(config.get("alpha", 0.2) if config.get("alpha") is not None else 0.2),
                sampling_seed=int(
                    config.get("sampling_seed", 42) if config.get("sampling_seed") is not None else 42
                ),
                invert_entropy=bool(config.get("invert_entropy", True)),
            )
        else:
            raise TypeError(f"Invalid config type: {type(config)}")

        self.benign_pool = list(benign_pool) if benign_pool is not None else None
        self.model_service = model_service

    def _get_model_fn(self, model_service: Any = None) -> Callable[[list[float]], float | tuple[float, Any]]:
        target_model = model_service or self.model_service
        if target_model is None:
            raise ValueError("M2 requires a model_service or model_fn to perform inference on perturbed samples.")

        if hasattr(target_model, "predict_proba"):
            return target_model.predict_proba
        if hasattr(target_model, "infer"):
            return target_model.infer
        if callable(target_model):
            return target_model
        raise TypeError(
            f"Model service must be callable or provide an infer() or predict_proba() method, got {type(target_model)}"
        )

    def _get_benign_pool(self, benign_pool: Sequence[Sequence[float]] | None = None, dim: int = 2381) -> list[list[float]]:
        pool = benign_pool if benign_pool is not None else self.benign_pool
        if pool is not None and len(pool) > 0:
            return [list(sample) for sample in pool]

        # Generate a deterministic synthetic baseline pool when none is provided (e.g., demo/isolated tests)
        # 16 standard neutral samples with small Gaussian perturbation centered around 0.0
        rng = random.Random(self.config.sampling_seed)
        synth_pool: list[list[float]] = []
        for _ in range(max(self.config.n_mix, 8)):
            synth_pool.append([rng.gauss(0.0, 0.05) for _ in range(dim)])
        return synth_pool

    def score(
        self,
        vector: Sequence[float],
        model_service: Any = None,
        benign_pool: Sequence[Sequence[float]] | None = None,
    ) -> float:
        res = self.detect(vector, model_service=model_service, benign_pool=benign_pool)
        return res.score

    def detect(
        self,
        vector: Sequence[float],
        model_service: Any = None,
        benign_pool: Sequence[Sequence[float]] | None = None,
    ) -> SignalResult:
        if not self.config.enabled:
            return SignalResult(name=self.name, score=0.0, diagnostics={"status": "DISABLED"})

        clean_vec = [float(v) for v in vector]
        model_fn = self._get_model_fn(model_service)
        pool = self._get_benign_pool(benign_pool, dim=len(clean_vec))

        score, diagnostics = tabular_strip(
            vector=clean_vec,
            model_fn=model_fn,
            benign_pool=pool,
            n_mix=self.config.n_mix,
            alpha=self.config.alpha,
            sampling_seed=self.config.sampling_seed,
            invert_entropy=self.config.invert_entropy,
        )

        return SignalResult(name=self.name, score=score, diagnostics=diagnostics)
