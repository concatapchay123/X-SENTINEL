from __future__ import annotations

import math
from collections.abc import Sequence

FEATURE_COUNT = 2381


class VectorValidationError(ValueError):
    pass


def validate_vector(values: Sequence[float]) -> list[float]:
    if len(values) != FEATURE_COUNT:
        raise VectorValidationError(f"expected {FEATURE_COUNT} features, got {len(values)}")
    output: list[float] = []
    for idx, value in enumerate(values):
        try:
            fv = float(value)
        except (TypeError, ValueError) as exc:
            raise VectorValidationError(f"feature[{idx}] is not numeric") from exc
        if not math.isfinite(fv):
            raise VectorValidationError(f"feature[{idx}] is not finite")
        output.append(fv)
    return output
