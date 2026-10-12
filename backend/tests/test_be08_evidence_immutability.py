from __future__ import annotations

from dataclasses import FrozenInstanceError
import pytest

from x_sentinel.audit.evidence import CanonicalEvidence


def _valid_evidence_dict() -> dict:
    return {
        "request_id": "REQ-IMMUTABLE-001",
        "run_id": "RUN-IMMUTABLE-001",
        "timestamp": "2026-10-12T14:35:00.000000+00:00",
        "code_commit": "c0ffee1234567890abcdef1234567890abcdef12",
        "build_digest": "sha256:11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        "input_id": "sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "input_mode": "vector",
        "view_map_hash": "276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
        "model_hash": "509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
        "model_config_hash": "a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
        "detector_config_hash": "b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1",
        "seed": 42,
        "malware_score": 0.45,
        "signals": {"m1": 0.1, "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5},
        "fusion_score": 0.35,
        "threshold_id": "THRESH-01",
        "decision": "PASS",
        "latency_ms": {"end_to_end": 5.0},
        "demo_mode": False,
    }


class TestEvidenceImmutability:
    """Verifies immutable contract enforcement on canonical evidence."""

    def test_in_place_attribute_mutation_forbidden(self) -> None:
        evidence = CanonicalEvidence.from_dict(_valid_evidence_dict())

        with pytest.raises(FrozenInstanceError):
            evidence.malware_score = 0.99  # type: ignore

        with pytest.raises(FrozenInstanceError):
            evidence.decision = "QUARANTINE"  # type: ignore

        with pytest.raises(FrozenInstanceError):
            evidence.fusion_score = 0.88  # type: ignore

        with pytest.raises(FrozenInstanceError):
            evidence.seed = 999  # type: ignore

        with pytest.raises(FrozenInstanceError):
            evidence.demo_mode = True  # type: ignore

        with pytest.raises(FrozenInstanceError):
            evidence.evidence_hash = "f" * 64  # type: ignore

    def test_dictionary_mutation_does_not_mutate_evidence(self) -> None:
        evidence = CanonicalEvidence.from_dict(_valid_evidence_dict())
        d = evidence.to_dict()
        d["malware_score"] = 0.999
        d["decision"] = "QUARANTINE"

        assert evidence.malware_score == 0.45
        assert evidence.decision == "PASS"

    def test_with_hash_returns_new_instance(self) -> None:
        original = CanonicalEvidence.from_dict(_valid_evidence_dict())
        assert original.evidence_hash is None

        hashed = original.with_hash()
        assert hashed.evidence_hash is not None
        assert original.evidence_hash is None  # Original remains untouched
        assert hashed is not original
