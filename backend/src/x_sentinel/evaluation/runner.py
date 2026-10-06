from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationRunSpec:
    run_id: str
    experiment: str
    config_hash: str
    dataset_hash: str
    seed: int


class EvaluationRunner:
    """E0–E5 skeleton. Must persist raw outputs before metrics are computed."""

    def run(self, _spec: EvaluationRunSpec) -> None:
        raise NotImplementedError("PLAN-19")
