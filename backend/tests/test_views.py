from pathlib import Path
from x_sentinel.data.views import load_view_map


def test_demo_view_counts():
    path = Path("configs/views.demo.yaml")
    vm = load_view_map(path, allow_demo=True)
    parts = vm.split([0.0] * 2381)
    assert len(parts["structural"]) == 255
    assert len(parts["behavioral"]) == 1280
    assert len(parts["metadata"]) == 846
    assert sum(map(len, parts.values())) == 2381
