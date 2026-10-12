from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

FEATURE_COUNT = 2381


class VectorValidationError(ValueError):
    """Base error for all vector validation failures."""


class DimensionMismatchError(VectorValidationError):
    """Raised when the vector does not match the canonical 2,381 feature count."""

    def __init__(self, message: str, expected: int = FEATURE_COUNT, actual: int = 0) -> None:
        super().__init__(message)
        self.expected = expected
        self.actual = actual


class StructuralShapeError(VectorValidationError):
    """Raised when the input object has an invalid top-level structural shape."""


class InvalidDataTypeError(VectorValidationError):
    """Raised when a feature element has an invalid or non-numeric data type."""

    def __init__(
        self,
        message: str,
        index: int | None = None,
        actual_type: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.index = index
        self.actual_type = actual_type


class NonFiniteValueError(VectorValidationError):
    """Raised when a feature value is NaN, +Inf, or -Inf."""

    def __init__(self, message: str, index: int, value_type: str) -> None:
        super().__init__(message)
        self.index = index
        self.value_type = value_type


def validate_vector(values: Sequence[float] | Any) -> list[float]:
    """Validate that the input represents a canonical 2,381-dimensional float vector.

    Invariants:
    1. Exactly FEATURE_COUNT (2,381) features.
    2. Strictly preserved ordering (no sorting, reordering, or shuffling).
    3. Finite numeric values only (no NaN, +Inf, -Inf, or non-numeric types).
    4. Booleans, strings, bytes, dicts, None, and nested structures are rejected.
    5. Zero silent truncation, padding, clipping, or value modification.
    """
    if values is None:
        raise StructuralShapeError("vector input is None")

    if isinstance(values, (str, bytes, bytearray, dict, set)):
        raise StructuralShapeError(
            f"input type '{type(values).__name__}' is not a valid vector sequence"
        )

    if not hasattr(values, "__len__") or not hasattr(values, "__iter__"):
        raise StructuralShapeError(
            f"input object of type '{type(values).__name__}' is not a sequence"
        )

    actual_len = len(values)
    if actual_len != FEATURE_COUNT:
        if actual_len < FEATURE_COUNT:
            missing = FEATURE_COUNT - actual_len
            raise DimensionMismatchError(
                f"expected {FEATURE_COUNT} features, got {actual_len} (missing {missing} features)",
                expected=FEATURE_COUNT,
                actual=actual_len,
            )
        extra = actual_len - FEATURE_COUNT
        raise DimensionMismatchError(
            f"expected {FEATURE_COUNT} features, got {actual_len} (extra {extra} features)",
            expected=FEATURE_COUNT,
            actual=actual_len,
        )

    output: list[float] = []
    for idx, value in enumerate(values):
        if isinstance(value, bool):
            raise InvalidDataTypeError(
                f"feature[{idx}] is a boolean, expected numeric float",
                index=idx,
                actual_type="bool",
            )
        if isinstance(value, (str, bytes, bytearray)):
            raise InvalidDataTypeError(
                f"feature[{idx}] is a string/bytes, expected numeric float",
                index=idx,
                actual_type=type(value).__name__,
            )
        try:
            fv = float(value)
        except (TypeError, ValueError) as exc:
            raise InvalidDataTypeError(
                f"feature[{idx}] is not numeric: {type(value).__name__}",
                index=idx,
                actual_type=type(value).__name__,
            ) from exc

        if math.isnan(fv):
            raise NonFiniteValueError(f"feature[{idx}] is NaN", index=idx, value_type="nan")
        if math.isinf(fv):
            raise NonFiniteValueError(f"feature[{idx}] is infinite", index=idx, value_type="inf")

        output.append(fv)

    return output


def validate_vector_batch(batch: Sequence[Sequence[float]] | Any) -> list[list[float]]:
    """Validate a batch of 2,381-dimensional vectors, preserving order and structure."""
    if batch is None:
        raise StructuralShapeError("batch input is None")

    if isinstance(batch, (str, bytes, bytearray, dict)):
        raise StructuralShapeError(f"batch type '{type(batch).__name__}' is not a valid sequence")

    if not hasattr(batch, "__len__") or not hasattr(batch, "__iter__"):
        raise StructuralShapeError(
            f"batch object of type '{type(batch).__name__}' is not a sequence"
        )

    return [validate_vector(item) for item in batch]


def validate_named_features(
    mapping: dict[str, Any],
    feature_names: Sequence[str],
) -> list[float]:
    """Validate a dictionary of named features against an authoritative ordered feature list.

    Reconstructs the canonical ordered 2,381 vector strictly based on feature_names.
    """
    if not isinstance(mapping, dict):
        raise StructuralShapeError("named features input must be a dictionary")

    expected_len = len(feature_names)
    actual_len = len(mapping)

    if actual_len != expected_len:
        if actual_len < expected_len:
            missing_keys = set(feature_names) - set(mapping.keys())
            raise DimensionMismatchError(
                f"expected {expected_len} named features, got {actual_len} "
                f"(missing {len(missing_keys)})",
                expected=expected_len,
                actual=actual_len,
            )
        extra_keys = set(mapping.keys()) - set(feature_names)
        raise DimensionMismatchError(
            f"expected {expected_len} named features, got {actual_len} "
            f"(extra {len(extra_keys)})",
            expected=expected_len,
            actual=actual_len,
        )

    ordered_values: list[float] = []
    for name in feature_names:
        if name not in mapping:
            raise DimensionMismatchError(
                f"missing required feature '{name}'",
                expected=expected_len,
                actual=actual_len,
            )
        ordered_values.append(mapping[name])

    return validate_vector(ordered_values)


@dataclass(frozen=True)
class VectorSchema:
    """Canonical vector schema encapsulation for X-SENTINEL V3."""

    feature_count: int = FEATURE_COUNT
    dtype: str = "float64"

    def validate(self, values: Sequence[float] | Any) -> list[float]:
        return validate_vector(values)

    def validate_batch(self, batch: Sequence[Sequence[float]] | Any) -> list[list[float]]:
        return validate_vector_batch(batch)
