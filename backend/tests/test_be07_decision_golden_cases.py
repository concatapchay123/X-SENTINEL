from __future__ import annotations

import pytest
from x_sentinel.fusion.decision import DecisionPolicy, DecisionResult, DecisionVerdict
from x_sentinel.fusion.engine import FusionEngine
from x_sentinel.fusion.golden_cases import GOLDEN_DECISION_CASES, GoldenCase


class TestGoldenDecisionCases:
    """Rigorous verification of canonical Golden Decision Cases."""

    @pytest.mark.parametrize("case", GOLDEN_DECISION_CASES, ids=lambda c: c.case_id)
    def test_golden_case_execution(self, case: GoldenCase) -> None:
        engine = FusionEngine()

        # Step 1: Compute fusion score
        fusion_score = engine.score(case.signals)
        assert abs(fusion_score - case.expected_fusion_score) < 1e-6, (
            f"Fusion score mismatch for {case.case_id}: "
            f"expected {case.expected_fusion_score}, got {fusion_score}"
        )

        # Step 2: Evaluate decision policy
        policy = DecisionPolicy(
            alert_threshold=case.alert_threshold,
            quarantine_threshold=case.quarantine_threshold,
            demo_mode=case.demo_mode,
        )
        decision_res = policy.evaluate(fusion_score)

        assert isinstance(decision_res, DecisionResult)
        assert decision_res.decision == case.expected_decision, (
            f"Decision mismatch for {case.case_id}: "
            f"expected {case.expected_decision}, got {decision_res.decision}"
        )
        assert decision_res.candidate_verdict == case.expected_candidate_verdict, (
            f"Candidate verdict mismatch for {case.case_id}: "
            f"expected {case.expected_candidate_verdict}, got {decision_res.candidate_verdict}"
        )
        assert decision_res.demo_mode == case.demo_mode

    def test_golden_case_catalog_integrity(self) -> None:
        case_ids = [c.case_id for c in GOLDEN_DECISION_CASES]
        # Must have unique IDs
        assert len(case_ids) == len(set(case_ids))
        # Must include at least 8 canonical cases
        assert len(GOLDEN_DECISION_CASES) >= 8

    def test_batch_vs_single_decision_consistency(self) -> None:
        policy = DecisionPolicy(alert_threshold=0.50, quarantine_threshold=0.85, demo_mode=False)
        scores = [0.10, 0.49, 0.50, 0.70, 0.85, 0.95]

        # Single evaluations
        single_verdicts = [policy.evaluate(s).decision for s in scores]

        # Batch evaluation
        batch_verdicts = [policy.evaluate(s).decision for s in scores]

        assert single_verdicts == batch_verdicts
        assert single_verdicts == [
            DecisionVerdict.PASS.value,
            DecisionVerdict.PASS.value,
            DecisionVerdict.ALERT.value,
            DecisionVerdict.ALERT.value,
            DecisionVerdict.QUARANTINE.value,
            DecisionVerdict.QUARANTINE.value,
        ]
