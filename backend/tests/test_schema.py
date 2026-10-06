import math
import pytest
from x_sentinel.data.schema import FEATURE_COUNT, VectorValidationError, validate_vector


def test_accepts_2381_finite_values():
    out = validate_vector([0.0] * FEATURE_COUNT)
    assert len(out) == FEATURE_COUNT


def test_rejects_wrong_length():
    with pytest.raises(VectorValidationError):
        validate_vector([0.0] * (FEATURE_COUNT - 1))


def test_rejects_non_finite():
    values = [0.0] * FEATURE_COUNT
    values[3] = math.inf
    with pytest.raises(VectorValidationError):
        validate_vector(values)
