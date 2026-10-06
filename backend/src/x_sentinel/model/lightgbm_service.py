from __future__ import annotations

from pathlib import Path


class LightGBMService:
    """Scientific model adapter. Implementation belongs to PLAN-08."""

    def __init__(self, model_path: Path, expected_sha256: str):
        self.model_path = model_path
        self.expected_sha256 = expected_sha256
        raise NotImplementedError("Freeze model/config/hash before scientific adapter is enabled")
