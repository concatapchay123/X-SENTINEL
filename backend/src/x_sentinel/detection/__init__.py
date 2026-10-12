from __future__ import annotations

from x_sentinel.detection.config import (
    DetectorConfig,
    M1Config,
    M2Config,
    M3Config,
    M4Config,
    M5Config,
    compute_detector_config_hash,
    load_detector_config,
)
from x_sentinel.detection.m1_tadr import M1TADRDetector, m1_tadr
from x_sentinel.detection.m2_strip import M2StripDetector, binary_entropy, tabular_strip
from x_sentinel.detection.m3_view import (
    M3ViewDetector,
    m3_view_concentration,
    view_contributions,
    view_entropy,
)
from x_sentinel.detection.m4_cross_view import (
    M4CrossViewDetector,
    behavioral_metadata_gap,
    full_vs_behavioral_gap,
    max_pairwise_difference,
    symmetric_cross_view_disagreement,
    view_std,
)
from x_sentinel.detection.m5_semantic import (
    M5RulesIntegrityError,
    M5SemanticPlausibilityDetector,
    evaluate_semantic_rules,
    load_m5_rules,
)
from x_sentinel.detection.pipeline import DetectorPipeline

__all__ = [
    # M1
    "m1_tadr",
    "M1TADRDetector",
    # M2
    "binary_entropy",
    "tabular_strip",
    "M2StripDetector",
    # M3
    "view_contributions",
    "m3_view_concentration",
    "view_entropy",
    "M3ViewDetector",
    # M4
    "symmetric_cross_view_disagreement",
    "view_std",
    "behavioral_metadata_gap",
    "full_vs_behavioral_gap",
    "max_pairwise_difference",
    "M4CrossViewDetector",
    # M5
    "load_m5_rules",
    "evaluate_semantic_rules",
    "M5SemanticPlausibilityDetector",
    "M5RulesIntegrityError",
    # Configuration
    "DetectorConfig",
    "M1Config",
    "M2Config",
    "M3Config",
    "M4Config",
    "M5Config",
    "load_detector_config",
    "compute_detector_config_hash",
    # Pipeline
    "DetectorPipeline",
]
