from x_sentinel.detection.m1_tadr import m1_tadr


def test_m1_tadr_basic():
    assert m1_tadr([1.0, 1.0, 2.0]) == 0.5


def test_m1_tadr_zero():
    assert m1_tadr([0.0, 0.0]) == 0.0
