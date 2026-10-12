from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from x_sentinel.fusion.calibration import (
    CalibrationArtifact,
    CalibrationEngine,
    CalibrationError,
    CalibrationIntegrityError,
    CalibrationUnresolvedError,
    D0Calibration,
    D1Calibration,
    InsufficientDataError,
    wilson_score_interval,
)
from x_sentinel.fusion.config import CalibrationConfig


class TestWilsonScoreInterval:
    """Mathematical verification of Wilson score 95% confidence interval."""

    def test_wilson_exact_known_values(self) -> None:
        # Known textbook case: 10 successes in 1000 trials (p_hat = 0.01)
        low, high = wilson_score_interval(10, 1000, confidence=0.95)
        assert 0.005 < low < 0.006
        assert 0.018 < high < 0.019
        assert low < 0.01 < high

    def test_wilson_boundary_zero_successes(self) -> None:
        low, high = wilson_score_interval(0, 100, confidence=0.95)
        assert low == 0.0
        assert 0.0 < high < 0.05

    def test_wilson_boundary_all_successes(self) -> None:
        low, high = wilson_score_interval(100, 100, confidence=0.95)
        assert 0.95 < low < 1.0
        assert high == 1.0

    def test_wilson_symmetry_at_fifty_percent(self) -> None:
        low, high = wilson_score_interval(50, 100, confidence=0.95)
        # Symmetrical around 0.5
        assert abs((0.5 - low) - (high - 0.5)) < 1e-6

    def test_wilson_rejects_invalid_inputs(self) -> None:
        with pytest.raises(ValueError, match="strictly positive"):
            wilson_score_interval(5, 0)
        with pytest.raises(ValueError, match="strictly positive"):
            wilson_score_interval(5, -10)
        with pytest.raises(ValueError, match="successes must be in"):
            wilson_score_interval(-1, 100)
        with pytest.raises(ValueError, match="successes must be in"):
            wilson_score_interval(105, 100)


class TestD0Calibration:
    """Verification of D0 Alert Budget mode (no trusted reference)."""

    def test_d0_returns_configured_budget_threshold(self) -> None:
        thresh = D0Calibration.get_threshold(0.50)
        assert thresh == 0.50

    def test_d0_rejects_out_of_domain_threshold(self) -> None:
        with pytest.raises(CalibrationError, match="must be in"):
            D0Calibration.get_threshold(-0.1)
        with pytest.raises(CalibrationError, match="must be in"):
            D0Calibration.get_threshold(1.2)


class TestD1CalibrationFitting:
    """Verification of empirical D1 quantile calibration on benign validation sets."""

    def test_d1_fit_satisfies_fpr_target(self) -> None:
        np.random.seed(42)
        benign_scores = np.random.beta(a=1.5, b=8.0, size=1000).tolist()
        artifact = D1Calibration.fit(benign_scores, target_fpr=0.01)

        assert isinstance(artifact, CalibrationArtifact)
        assert artifact.mode == "d1"
        assert artifact.target_fpr == 0.01
        assert artifact.sample_count == 1000
        assert artifact.empirical_fpr <= 0.01
        assert 0.0 <= artifact.threshold <= 1.0
        assert artifact.wilson_ci_low < artifact.empirical_fpr < artifact.wilson_ci_high
        assert len(artifact.payload_sha256) == 64

    def test_d1_fit_reproducible_given_same_inputs(self) -> None:
        scores = [0.1 * (i % 10) for i in range(100)]
        art1 = D1Calibration.fit(scores, target_fpr=0.05, dataset_hash="fixed_hash")
        art2 = D1Calibration.fit(scores, target_fpr=0.05, dataset_hash="fixed_hash")

        assert art1.threshold == art2.threshold
        assert art1.empirical_fpr == art2.empirical_fpr
        assert art1.wilson_ci_low == art2.wilson_ci_low
        assert art1.wilson_ci_high == art2.wilson_ci_high

    def test_d1_fit_rejects_insufficient_samples(self) -> None:
        with pytest.raises(InsufficientDataError, match="cannot be empty"):
            D1Calibration.fit([])
        with pytest.raises(InsufficientDataError, match="At least 10 benign samples"):
            D1Calibration.fit([0.1, 0.2, 0.3])

    def test_d1_fit_rejects_invalid_fpr_target(self) -> None:
        scores = [0.1] * 20
        with pytest.raises(CalibrationError, match="target_fpr must be in"):
            D1Calibration.fit(scores, target_fpr=0.0)
        with pytest.raises(CalibrationError, match="target_fpr must be in"):
            D1Calibration.fit(scores, target_fpr=1.0)
        with pytest.raises(CalibrationError, match="target_fpr must be in"):
            D1Calibration.fit(scores, target_fpr=-0.05)

    def test_d1_fit_rejects_non_finite_scores(self) -> None:
        with pytest.raises(CalibrationError, match="Non-finite score"):
            D1Calibration.fit([0.1] * 10 + [float("nan")])
        with pytest.raises(CalibrationError, match="Non-finite score"):
            D1Calibration.fit([0.1] * 10 + [float("inf")])

    def test_d1_fit_rejects_out_of_domain_scores(self) -> None:
        with pytest.raises(CalibrationError, match="Score out of domain"):
            D1Calibration.fit([0.1] * 10 + [1.5])
        with pytest.raises(CalibrationError, match="Score out of domain"):
            D1Calibration.fit([0.1] * 10 + [-0.01])


class TestCalibrationArtifactPersistenceAndIntegrity:
    """Verification of serialization, loading, and checksum verification."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        scores = [0.05 * i for i in range(20)]
        artifact = D1Calibration.fit(scores, target_fpr=0.05, artifact_id="test-art-1")
        save_path = tmp_path / "calib.json"
        artifact.save(save_path)

        loaded = CalibrationArtifact.load(save_path)
        assert loaded.artifact_id == artifact.artifact_id
        assert loaded.threshold == artifact.threshold
        assert loaded.empirical_fpr == artifact.empirical_fpr
        assert loaded.payload_sha256 == artifact.payload_sha256

    def test_load_rejects_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            CalibrationArtifact.load(tmp_path / "non_existent.json")

    def test_load_rejects_tampered_payload(self, tmp_path: Path) -> None:
        scores = [0.05 * i for i in range(20)]
        artifact = D1Calibration.fit(scores, target_fpr=0.05, artifact_id="test-art-2")
        save_path = tmp_path / "tampered.json"
        artifact.save(save_path)

        # Alter the threshold inside the saved JSON
        content = json.loads(save_path.read_text(encoding="utf-8"))
        content["threshold"] = 0.999
        save_path.write_text(json.dumps(content), encoding="utf-8")

        with pytest.raises(CalibrationIntegrityError, match="checksum mismatch"):
            CalibrationArtifact.load(save_path)

    def test_load_rejects_malformed_json(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("NOT_JSON", encoding="utf-8")
        with pytest.raises(CalibrationIntegrityError, match="Corrupted calibration artifact"):
            CalibrationArtifact.load(bad_path)

    def test_load_rejects_missing_required_keys(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "incomplete.json"
        bad_path.write_text(json.dumps({"artifact_id": "incomplete"}), encoding="utf-8")
        with pytest.raises(CalibrationIntegrityError, match="Missing required key"):
            CalibrationArtifact.load(bad_path)


class TestCalibrationEngine:
    """Verification of CalibrationEngine lifecycle under D0 and D1 policies."""

    def test_engine_d0_mode(self) -> None:
        cfg = CalibrationConfig(mode="d0", d0_threshold=0.55)
        engine = CalibrationEngine(cfg, demo_mode=False)
        assert engine.active_threshold == 0.55
        assert engine.resolve() == 0.55

    def test_engine_d1_mode_with_explicit_threshold(self) -> None:
        cfg = CalibrationConfig(mode="d1", d1_threshold=0.62)
        engine = CalibrationEngine(cfg, demo_mode=False)
        assert engine.active_threshold == 0.62
        assert engine.resolve() == 0.62

    def test_engine_d1_mode_loads_valid_artifact(self) -> None:
        artifact_path = Path("artifacts/calibration/d1_calibration.json")
        if not artifact_path.exists():
            pytest.skip("Default D1 calibration artifact not found")
        cfg = CalibrationConfig(mode="d1", d1_artifact_path=str(artifact_path))
        engine = CalibrationEngine(cfg, demo_mode=False)
        assert engine.active_threshold is not None
        assert 0.0 <= engine.resolve() <= 1.0
        assert engine.artifact is not None
        assert engine.artifact.mode == "d1"

    def test_engine_d1_mode_fails_closed_in_scientific_when_unresolved(self) -> None:
        cfg = CalibrationConfig(
            mode="d1", d1_threshold=None, d1_artifact_path="artifacts/missing.json"
        )
        with pytest.raises(CalibrationUnresolvedError, match="missing at"):
            CalibrationEngine(cfg, demo_mode=False)

    def test_engine_d1_mode_falls_back_in_demo_mode_with_d0_threshold(self) -> None:
        cfg = CalibrationConfig(
            mode="d1",
            d0_threshold=0.50,
            d1_threshold=None,
            d1_artifact_path="artifacts/missing.json",
        )
        engine = CalibrationEngine(cfg, demo_mode=True)
        assert engine.active_threshold is None
        # Resolves to D0 fallback threshold in demo mode
        assert engine.resolve() == 0.50
