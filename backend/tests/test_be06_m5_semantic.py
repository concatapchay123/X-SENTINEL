from __future__ import annotations

import json
from pathlib import Path

import pytest
from x_sentinel.detection.config import M5Config
from x_sentinel.detection.m5_semantic import (
    M5RulesIntegrityError,
    M5SemanticPlausibilityDetector,
    evaluate_semantic_rules,
    load_m5_rules,
)
from x_sentinel.domain import SignalResult

RULES_PATH = Path("configs/m5_rules.json")
CANONICAL_SHA256 = "2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d"


class TestM5RulesLoadingAndIntegrity:
    """Verification of the pre-locked rules artifact and SHA-256 cryptographic gate."""

    def test_load_canonical_rules_artifact_matches_sha256(self) -> None:
        rules_data, digest = load_m5_rules(RULES_PATH, expected_sha256=CANONICAL_SHA256)
        assert digest == CANONICAL_SHA256
        assert isinstance(rules_data, dict)
        assert len(rules_data["rules"]) >= 8

    def test_missing_rules_artifact_raises_file_not_found(self, tmp_path: Path) -> None:
        missing_file = tmp_path / "non_existent_rules.json"
        with pytest.raises(FileNotFoundError, match="not found"):
            load_m5_rules(missing_file, expected_sha256=CANONICAL_SHA256)

    def test_tampered_rules_artifact_raises_integrity_error(self, tmp_path: Path) -> None:
        tampered_file = tmp_path / "tampered_rules.json"
        tampered_content = json.dumps({"rules": [{"rule_id": "TAMPERED"}]})
        tampered_file.write_text(tampered_content, encoding="utf-8")

        with pytest.raises(M5RulesIntegrityError, match="checksum mismatch"):
            load_m5_rules(tampered_file, expected_sha256=CANONICAL_SHA256)

    def test_corrupted_json_raises_value_error(self, tmp_path: Path) -> None:
        corrupted_file = tmp_path / "corrupted_rules.json"
        corrupted_file.write_text("{ broken json: [", encoding="utf-8")
        with pytest.raises(ValueError, match="Corrupted or invalid JSON"):
            load_m5_rules(corrupted_file)


class TestM5SemanticPlausibilityRules:
    """Verification of PE domain invariants and physical constraint rules."""

    @pytest.fixture
    def canonical_rules(self) -> dict:
        data, _ = load_m5_rules(RULES_PATH, expected_sha256=CANONICAL_SHA256)
        return data

    def test_clean_compliant_vector_yields_full_plausibility(self, canonical_rules: dict) -> None:
        # A plausible feature vector: all features zero or valid positive bounds
        clean_vector = [0.0] * 2381
        score, diag = evaluate_semantic_rules(clean_vector, canonical_rules)

        assert score == 1.0
        assert diag["rules_failed"] == 0
        assert diag["rules_passed"] == diag["rules_evaluated"]
        assert len(diag["violations"]) == 0
        assert diag["plausibility_score"] == 1.0
        assert diag["anomaly_score"] == 0.0

    def test_violating_negative_byte_histogram(self, canonical_rules: dict) -> None:
        vec = [0.0] * 2381
        vec[10] = -0.5  # Negative byte frequency is impossible in PE

        score, diag = evaluate_semantic_rules(vec, canonical_rules)
        assert score < 1.0
        assert diag["rules_failed"] >= 1
        violated_ids = [v["rule_id"] for v in diag["violations"]]
        assert "RULE-01-BYTE-HISTOGRAM-NON-NEGATIVE" in violated_ids

    def test_violating_impossible_byte_entropy(self, canonical_rules: dict) -> None:
        vec = [0.0] * 2381
        # Shannon entropy for a byte is strictly <= log2(256) = 8.0 bits
        vec[300] = 15.0  # Physically impossible entropy

        score, diag = evaluate_semantic_rules(vec, canonical_rules)
        assert score < 1.0
        violated_ids = [v["rule_id"] for v in diag["violations"]]
        assert "RULE-02-BYTE-ENTROPY-HISTOGRAM-BOUNDS" in violated_ids

    def test_violating_negative_file_size(self, canonical_rules: dict) -> None:
        vec = [0.0] * 2381
        vec[2175] = -500.0  # Negative file size

        score, diag = evaluate_semantic_rules(vec, canonical_rules)
        assert score < 1.0
        violated_ids = [v["rule_id"] for v in diag["violations"]]
        assert "RULE-03-GENERAL-FILE-SIZE-NON-NEGATIVE" in violated_ids

    def test_violating_invalid_boolean_flags(self, canonical_rules: dict) -> None:
        vec = [0.0] * 2381
        vec[2180] = 55.0  # has_relocations must be binary in [0, 1]

        score, diag = evaluate_semantic_rules(vec, canonical_rules)
        assert score < 1.0
        violated_ids = [v["rule_id"] for v in diag["violations"]]
        assert "RULE-05-BOOLEAN-FLAGS-BOUNDS" in violated_ids

    def test_violating_negative_section_size(self, canonical_rules: dict) -> None:
        vec = [0.0] * 2381
        vec[550] = -1000.0  # Section size negative

        score, diag = evaluate_semantic_rules(vec, canonical_rules)
        assert score < 1.0
        violated_ids = [v["rule_id"] for v in diag["violations"]]
        assert "RULE-07-SECTION-SIZES-NON-NEGATIVE" in violated_ids


class TestM5SemanticNegativeCases:
    """Negative input validation for M5."""

    @pytest.fixture
    def canonical_rules(self) -> dict:
        data, _ = load_m5_rules(RULES_PATH, expected_sha256=CANONICAL_SHA256)
        return data

    def test_rejects_vector_dimension_mismatch(self, canonical_rules: dict) -> None:
        with pytest.raises(ValueError, match="dimension mismatch"):
            evaluate_semantic_rules([0.0] * 100, canonical_rules)

    def test_rejects_non_finite_values(self, canonical_rules: dict) -> None:
        vec = [0.0] * 2381
        vec[0] = float("nan")
        with pytest.raises(ValueError, match="non-finite"):
            evaluate_semantic_rules(vec, canonical_rules)


class TestM5SemanticPlausibilityDetectorClass:
    """Contract verification for M5SemanticPlausibilityDetector class."""

    def test_detector_initialization_with_canonical_config(self) -> None:
        detector = M5SemanticPlausibilityDetector()
        assert detector.name == "m5"
        assert detector.loaded_sha256 == CANONICAL_SHA256

        vec = [0.0] * 2381
        res = detector.detect(vec)

        assert isinstance(res, SignalResult)
        assert res.name == "m5"
        assert res.score == 1.0
        assert res.diagnostics["rules_sha256"] == CANONICAL_SHA256
        assert res.diagnostics["rules_passed"] == res.diagnostics["rules_evaluated"]

    def test_detector_detects_violation_and_reports_provenance(self) -> None:
        detector = M5SemanticPlausibilityDetector()
        vec = [0.0] * 2381
        vec[10] = -1.0  # Negative byte frequency

        res = detector.detect(vec)
        assert res.score < 1.0
        assert res.diagnostics["rules_failed"] >= 1
        assert len(res.diagnostics["violations"]) >= 1

    def test_detector_score_convenience_method(self) -> None:
        detector = M5SemanticPlausibilityDetector()
        assert detector.score([0.0] * 2381) == 1.0

    def test_detector_disabled_returns_zero(self) -> None:
        cfg = M5Config(enabled=False)
        detector = M5SemanticPlausibilityDetector(cfg)
        res = detector.detect([0.0] * 2381)
        assert res.score == 0.0
        assert res.diagnostics["status"] == "DISABLED"
