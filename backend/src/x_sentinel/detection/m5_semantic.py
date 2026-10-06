class M5SemanticPlausibilityDetector:
    """Requires a pre-locked rules/bins artifact and hash."""

    def score(self, *_args, **_kwargs) -> float:
        raise NotImplementedError("PLAN-14: lock M5 rules/bins before enabling")
