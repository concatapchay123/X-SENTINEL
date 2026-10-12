from __future__ import annotations

import math
import pytest

from x_sentinel.audit.evidence import (
    ALLOWED_DECISIONS,
    ALLOWED_INPUT_MODES,
    CANONICAL_DECISIONS,
    CanonicalEvidence,
    EvidenceValidationError,
    ScientificEvidenceRejectedError,
)


def _valid_evidence_dict() -> dict:
    return {
        "request_id": "REQ-2026-TEST-001",
        "run_id": "RUN-2026-TEST-A1",
        "timestamp": "2026-10-12T14:30:00.000000+00:00",
        "code_commit": "c0ffee1234567890abcdef1234567890abcdef12",
        "build_digest": "sha256:11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        "input_id": "sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "input_mode": "vector",
        "view_map_hash": "276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
        "model_hash": "509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
        "model_config_hash": "a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
        "detector_config_hash": "b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1",
        "seed": 42,
        "malware_score": 0.825,
        "signals": {
            "m1": 0.12,
            "m2": 0.34,
            "m3": 0.56,
            "m4": 0.78,
            "m5": 0.90,
        },
        "fusion_score": 0.654,
        "threshold_id": "THRESH-D1-OPT-0.50",
        "decision": "ALERT",
        "latency_ms": {"end_to_end": 7.42, "m1": 1.2, "fusion": 0.8},
        "demo_mode": False,
    }


class TestCanonicalEvidenceContract:
    """Verifies that CanonicalEvidence strictly satisfies 27_EVIDENCE_SCHEMA.md."""

    def test_valid_evidence_creation_and_fields(self) -> None:
        raw = _valid_evidence_dict()
        evidence = CanonicalEvidence.from_dict(raw)

        assert evidence.request_id == "REQ-2026-TEST-001"
        assert evidence.run_id == "RUN-2026-TEST-A1"
        assert evidence.timestamp == "2026-10-12T14:30:00.000000+00:00"
        assert evidence.code_commit == "c0ffee1234567890abcdef1234567890abcdef12"
        assert evidence.build_digest.startswith("sha256:")
        assert evidence.input_id.startswith("sha256:")
        assert evidence.input_mode == "vector"
        assert evidence.seed == 42
        assert evidence.malware_score == 0.825
        assert evidence.signals["m1"] == 0.12
        assert evidence.fusion_score == 0.654
        assert evidence.threshold_id == "THRESH-D1-OPT-0.50"
        assert evidence.decision == "ALERT"
        assert evidence.latency_ms["end_to_end"] == 7.42
        assert evidence.demo_mode is False
        assert evidence.evidence_hash is None

    def test_missing_required_fields_rejected(self) -> None:
        required_fields = (
            "request_id",
            "run_id",
            "timestamp",
            "code_commit",
            "build_digest",
            "input_id",
            "input_mode",
            "view_map_hash",
            "model_hash",
            "model_config_hash",
            "detector_config_hash",
            "seed",
            "malware_score",
            "signals",
            "fusion_score",
            "threshold_id",
            "decision",
            "latency_ms",
            "demo_mode",
        )
        for field in required_fields:
            data = _valid_evidence_dict()
            del data[field]
            with pytest.raises(EvidenceValidationError, match=f"Missing required fields.*'{field}'"):
                CanonicalEvidence.from_dict(data)

    def test_empty_string_identities_rejected(self) -> None:
        string_fields = (
            "request_id",
            "run_id",
            "code_commit",
            "build_digest",
            "input_id",
            "view_map_hash",
            "model_hash",
            "model_config_hash",
            "detector_config_hash",
            "threshold_id",
        )
        for field in string_fields:
            data = _valid_evidence_dict()
            data[field] = "   "
            with pytest.raises(EvidenceValidationError, match=f"Field '{field}' must be a non-empty string"):
                CanonicalEvidence.from_dict(data)

    def test_invalid_timestamp_rejected(self) -> None:
        data = _valid_evidence_dict()
        data["timestamp"] = "not-a-timestamp"
        with pytest.raises(EvidenceValidationError, match="not a valid ISO 8601 format"):
            CanonicalEvidence.from_dict(data)

    def test_invalid_input_mode_rejected(self) -> None:
        data = _valid_evidence_dict()
        data["input_mode"] = "invalid_binary"
        with pytest.raises(EvidenceValidationError, match="input_mode must be one of"):
            CanonicalEvidence.from_dict(data)

    def test_invalid_malware_score_bounds(self) -> None:
        for bad_score in (-0.01, 1.01, float("nan"), float("inf"), -float("inf")):
            data = _valid_evidence_dict()
            data["malware_score"] = bad_score
            with pytest.raises(EvidenceValidationError, match="malware_score must be a finite float in"):
                CanonicalEvidence.from_dict(data)

    def test_invalid_fusion_score_bounds(self) -> None:
        for bad_score in (-0.1, 1.05, float("nan"), float("inf")):
            data = _valid_evidence_dict()
            data["fusion_score"] = bad_score
            with pytest.raises(EvidenceValidationError, match="fusion_score must be a finite float in"):
                CanonicalEvidence.from_dict(data)

    def test_signal_keys_contract(self) -> None:
        # Missing M5
        data = _valid_evidence_dict()
        data["signals"] = {"m1": 0.1, "m2": 0.2, "m3": 0.3, "m4": 0.4}
        with pytest.raises(EvidenceValidationError, match="signals must contain exactly keys"):
            CanonicalEvidence.from_dict(data)

        # Extra unexpected signal
        data = _valid_evidence_dict()
        data["signals"]["m6"] = 0.5
        with pytest.raises(EvidenceValidationError, match="signals must contain exactly keys"):
            CanonicalEvidence.from_dict(data)

        # Signal score out of bounds
        data = _valid_evidence_dict()
        data["signals"]["m3"] = 1.5
        with pytest.raises(EvidenceValidationError, match="signals\\['m3'\\] must be a finite float in"):
            CanonicalEvidence.from_dict(data)

    def test_decision_allowed_values(self) -> None:
        for dec in ("PASS", "ALERT", "QUARANTINE", "DEMO_ONLY"):
            data = _valid_evidence_dict()
            data["decision"] = dec
            ev = CanonicalEvidence.from_dict(data)
            assert ev.decision == dec

        data = _valid_evidence_dict()
        data["decision"] = "ALLOW_EXECUTION"
        with pytest.raises(EvidenceValidationError, match="decision must be one of"):
            CanonicalEvidence.from_dict(data)

    def test_latency_ms_validation(self) -> None:
        data = _valid_evidence_dict()
        data["latency_ms"] = {"m1": 1.0}  # missing end_to_end
        with pytest.raises(EvidenceValidationError, match="latency_ms must include 'end_to_end'"):
            CanonicalEvidence.from_dict(data)

        data = _valid_evidence_dict()
        data["latency_ms"] = {"end_to_end": -5.0}  # negative latency
        with pytest.raises(EvidenceValidationError, match="must be a non-negative finite float"):
            CanonicalEvidence.from_dict(data)

    def test_scientific_acceptance_rejection_of_demo_mode(self) -> None:
        """RULE: Acceptance scripts must reject demo_mode=true as scientific evidence."""
        data = _valid_evidence_dict()
        data["demo_mode"] = True
        evidence = CanonicalEvidence.from_dict(data)

        with pytest.raises(
            ScientificEvidenceRejectedError,
            match="Acceptance scripts must reject demo_mode=true as scientific evidence",
        ):
            evidence.validate_for_scientific_acceptance()

    def test_scientific_acceptance_rejection_of_demo_only_decision(self) -> None:
        data = _valid_evidence_dict()
        data["demo_mode"] = False
        data["decision"] = "DEMO_ONLY"
        evidence = CanonicalEvidence.from_dict(data)

        with pytest.raises(
            ScientificEvidenceRejectedError,
            match="Canonical scientific decision must be one of",
        ):
            evidence.validate_for_scientific_acceptance()

    def test_scientific_acceptance_passes_valid_canonical(self) -> None:
        for dec in ("PASS", "ALERT", "QUARANTINE"):
            data = _valid_evidence_dict()
            data["demo_mode"] = False
            data["decision"] = dec
            evidence = CanonicalEvidence.from_dict(data)
            evidence.validate_for_scientific_acceptance()  # Should not raise!

    def test_canonical_json_roundtrip(self) -> None:
        original = CanonicalEvidence.from_dict(_valid_evidence_dict())
        json_str = original.to_json()
        reconstructed = CanonicalEvidence.from_json(json_str)

        assert original.to_canonical_dict() == reconstructed.to_canonical_dict()
        assert original.compute_hash() == reconstructed.compute_hash()
