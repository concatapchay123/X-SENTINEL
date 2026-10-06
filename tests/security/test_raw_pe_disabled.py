import pytest
from x_sentinel.data.raw_pe import RawPEFeatureExtractor


def test_raw_pe_is_disabled_in_baseline():
    with pytest.raises(NotImplementedError):
        RawPEFeatureExtractor().extract("untrusted.exe")
