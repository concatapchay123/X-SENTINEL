class RawPEFeatureExtractor:
    """Phase-2 adapter. Static parsing only; never execute input binaries."""

    def extract(self, _path: str) -> list[float]:
        raise NotImplementedError(
            "Raw PE/LIEF extraction is feature-gated until TC-03/schema equivalence is approved"
        )
