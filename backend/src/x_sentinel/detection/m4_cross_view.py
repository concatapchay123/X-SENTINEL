class M4CrossViewDetector:
    """Canonical M4 is intentionally blocked until ADR-005 is accepted with an exact formula."""

    def score(self, *_args, **_kwargs) -> float:
        raise NotImplementedError("PLAN-13 / OQ-03: canonical M4 formula must be frozen")
