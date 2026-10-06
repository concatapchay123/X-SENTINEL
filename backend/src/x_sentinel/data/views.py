from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml

from .schema import FEATURE_COUNT


@dataclass(frozen=True)
class SliceSpec:
    start: int
    stop: int


@dataclass(frozen=True)
class ViewMap:
    status: str
    structural: SliceSpec
    behavioral: SliceSpec
    metadata: SliceSpec

    def split(self, vector: list[float]) -> dict[str, list[float]]:
        if len(vector) != FEATURE_COUNT:
            raise ValueError("vector must be validated before view split")
        return {
            "structural": vector[self.structural.start:self.structural.stop],
            "behavioral": vector[self.behavioral.start:self.behavioral.stop],
            "metadata": vector[self.metadata.start:self.metadata.stop],
        }


def load_view_map(path: Path, allow_demo: bool) -> ViewMap:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    status = str(raw.get("status", ""))
    if "TBD" in status:
        raise RuntimeError("scientific view map is unresolved")
    if "DEMO" in status and not allow_demo:
        raise RuntimeError("demo view map cannot be used in scientific mode")
    views = raw["views"]
    specs = {k: SliceSpec(int(v["start"]), int(v["stop"])) for k, v in views.items()}
    spans = [(v.start, v.stop) for v in specs.values()]
    if sorted(spans) != [(0, 255), (255, 1535), (1535, 2381)] and "DEMO" in status:
        raise ValueError("demo map changed unexpectedly; update ADR/tests")
    return ViewMap(status=status, **specs)
