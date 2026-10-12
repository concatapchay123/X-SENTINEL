from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GoldenCase:
    """Specification of an approved golden decision case."""

    case_id: str
    description: str
    signals: dict[str, float]
    expected_fusion_score: float
    alert_threshold: float | None
    quarantine_threshold: float
    demo_mode: bool
    expected_decision: str
    expected_candidate_verdict: str
    metadata: dict[str, Any]


GOLDEN_DECISION_CASES: list[GoldenCase] = [
    GoldenCase(
        case_id="GOLDEN-01-CLEAN-BENIGN",
        description="Clean sample with nominal detector background noise below alert threshold",
        signals={"m1": 0.02, "m2": 0.05, "m3": 0.01, "m4": 0.00, "m5": 0.00},
        expected_fusion_score=0.016,
        alert_threshold=0.50,
        quarantine_threshold=0.85,
        demo_mode=False,
        expected_decision="PASS",
        expected_candidate_verdict="PASS",
        metadata={"category": "benign_clear"},
    ),
    GoldenCase(
        case_id="GOLDEN-02-SUB-THRESHOLD-MARGINAL",
        description="Marginal sample strictly below alert threshold (0.490 < 0.500)",
        signals={"m1": 0.49, "m2": 0.49, "m3": 0.49, "m4": 0.49, "m5": 0.49},
        expected_fusion_score=0.490,
        alert_threshold=0.50,
        quarantine_threshold=0.85,
        demo_mode=False,
        expected_decision="PASS",
        expected_candidate_verdict="PASS",
        metadata={"category": "boundary_below"},
    ),
    GoldenCase(
        case_id="GOLDEN-03-EXACT-ALERT-BOUNDARY",
        description=(
            "Sample score strictly on alert threshold boundary (0.500 == 0.500) yielding ALERT"
        ),
        signals={"m1": 0.50, "m2": 0.50, "m3": 0.50, "m4": 0.50, "m5": 0.50},
        expected_fusion_score=0.500,
        alert_threshold=0.50,
        quarantine_threshold=0.85,
        demo_mode=False,
        expected_decision="ALERT",
        expected_candidate_verdict="ALERT",
        metadata={"category": "boundary_exact_alert"},
    ),
    GoldenCase(
        case_id="GOLDEN-04-ELEVATED-ALERT-SUSPICIOUS",
        description="Elevated trojan indicator across TADR and STRIP above alert threshold",
        signals={"m1": 0.80, "m2": 0.60, "m3": 0.70, "m4": 0.50, "m5": 0.40},
        expected_fusion_score=0.600,
        alert_threshold=0.50,
        quarantine_threshold=0.85,
        demo_mode=False,
        expected_decision="ALERT",
        expected_candidate_verdict="ALERT",
        metadata={"category": "suspicious_alert"},
    ),
    GoldenCase(
        case_id="GOLDEN-05-EXACT-QUARANTINE-BOUNDARY",
        description=(
            "Sample score strictly on quarantine boundary (0.850 == 0.850) yielding QUARANTINE"
        ),
        signals={"m1": 0.85, "m2": 0.85, "m3": 0.85, "m4": 0.85, "m5": 0.85},
        expected_fusion_score=0.850,
        alert_threshold=0.50,
        quarantine_threshold=0.85,
        demo_mode=False,
        expected_decision="QUARANTINE",
        expected_candidate_verdict="QUARANTINE",
        metadata={"category": "boundary_exact_quarantine"},
    ),
    GoldenCase(
        case_id="GOLDEN-06-MAXIMAL-SEVERE-TROJAN",
        description=(
            "Severe trojan trigger with high attribution dominance and zero plausibility"
        ),
        signals={"m1": 0.98, "m2": 0.95, "m3": 0.90, "m4": 0.92, "m5": 0.85},
        expected_fusion_score=0.920,
        alert_threshold=0.50,
        quarantine_threshold=0.85,
        demo_mode=False,
        expected_decision="QUARANTINE",
        expected_candidate_verdict="QUARANTINE",
        metadata={"category": "severe_quarantine"},
    ),
    GoldenCase(
        case_id="GOLDEN-07-DEMO-MODE-PRESERVATION",
        description=(
            "Suspicious sample in demo mode must return DEMO_ONLY while auditing candidate"
        ),
        signals={"m1": 0.80, "m2": 0.60, "m3": 0.70, "m4": 0.50, "m5": 0.40},
        expected_fusion_score=0.600,
        alert_threshold=0.50,
        quarantine_threshold=0.85,
        demo_mode=True,
        expected_decision="DEMO_ONLY",
        expected_candidate_verdict="ALERT",
        metadata={"category": "demo_isolation"},
    ),
    GoldenCase(
        case_id="GOLDEN-08-D1-CALIBRATED-BENIGN",
        description=(
            "Score 0.550 passes under D1 calibrated threshold 0.620 (suppressing false alarm)"
        ),
        signals={"m1": 0.55, "m2": 0.55, "m3": 0.55, "m4": 0.55, "m5": 0.55},
        expected_fusion_score=0.550,
        alert_threshold=0.62,
        quarantine_threshold=0.85,
        demo_mode=False,
        expected_decision="PASS",
        expected_candidate_verdict="PASS",
        metadata={"category": "d1_calibration_benefit"},
    ),
]
