from __future__ import annotations

import hashlib
import json
import pytest

from x_sentinel.audit.evidence import (
    CanonicalEvidence,
    EvidenceIntegrityError,
    compute_evidence_hash,
    verify_evidence_hash,
)


def _base_golden_dict() -> dict:
    return {
        "build_digest": "sha256:build_digest_golden_001",
        "code_commit": "c0ffee0000000000000000000000000000000000",
        "decision": "ALERT",
        "demo_mode": False,
        "detector_config_hash": "1111111111111111111111111111111111111111111111111111111111111111",
        "fusion_score": 0.725,
        "input_id": "sha256:input_digest_golden_001",
        "input_mode": "vector",
        "latency_ms": {"end_to_end": 8.5},
        "malware_score": 0.912,
        "model_config_hash": "2222222222222222222222222222222222222222222222222222222222222222",
        "model_hash": "3333333333333333333333333333333333333333333333333333333333333333",
        "request_id": "REQ-GOLDEN-EVIDENCE-01",
        "run_id": "RUN-GOLDEN-EVIDENCE-01",
        "seed": 42,
        "signals": {
            "m1": 0.15,
            "m2": 0.25,
            "m3": 0.35,
            "m4": 0.45,
            "m5": 0.55,
        },
        "threshold_id": "THRESH-GOLDEN-0.50",
        "timestamp": "2026-10-12T12:00:00+00:00",
        "view_map_hash": "4444444444444444444444444444444444444444444444444444444444444444",
    }


class TestEvidenceHashingAndIntegrity:
    """Acceptance tests for evidence hash calculation and integrity verification."""

    def test_evidence_hash_determinism_and_reproducibility(self) -> None:
        raw = _base_golden_dict()
        ev1 = CanonicalEvidence.from_dict(raw)
        ev2 = CanonicalEvidence.from_dict(raw)

        hash1 = ev1.compute_hash()
        hash2 = ev2.compute_hash()

        assert len(hash1) == 64
        assert hash1 == hash2
        assert compute_evidence_hash(ev1) == hash1
        assert compute_evidence_hash(raw) == hash1

    def test_canonical_key_ordering_invariance(self) -> None:
        """Verify that dictionary key insertion order does NOT change the resulting hash."""
        raw1 = _base_golden_dict()
        # Create reversed key order dictionary
        raw2 = {k: raw1[k] for k in reversed(list(raw1.keys()))}

        ev1 = CanonicalEvidence.from_dict(raw1)
        ev2 = CanonicalEvidence.from_dict(raw2)

        assert ev1.to_canonical_json() == ev2.to_canonical_json()
        assert ev1.compute_hash() == ev2.compute_hash()

    def test_golden_reference_hash_verification(self) -> None:
        raw = _base_golden_dict()
        ev = CanonicalEvidence.from_dict(raw)
        
        # Independently calculate canonical JSON and sha256
        canonical_dict = ev.to_canonical_dict()
        canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        expected_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        # Frozen golden reference hash
        assert expected_sha256 == "994e7f813be6702d9d4def0d93edc47ff4dc1fd5249af19e65768d106a59594e"

        computed = ev.compute_hash()
        assert computed == expected_sha256
        assert len(computed) == 64

        # Bind hash and verify
        bound_ev = ev.with_hash()
        assert bound_ev.evidence_hash == expected_sha256
        assert bound_ev.verify_integrity() is True
        assert verify_evidence_hash(bound_ev) is True
        assert verify_evidence_hash(bound_ev, expected_sha256) is True

    def test_tampering_detection_across_all_fields(self) -> None:
        """Tampering any field must result in hash mismatch and integrity failure."""
        golden_ev = CanonicalEvidence.from_dict(_base_golden_dict()).with_hash()
        original_hash = golden_ev.evidence_hash
        assert original_hash is not None

        tamper_cases = [
            ("request_id", "REQ-TAMPERED-01"),
            ("run_id", "RUN-TAMPERED-01"),
            ("timestamp", "2026-10-12T12:00:01+00:00"),
            ("code_commit", "deadbeef00000000000000000000000000000000"),
            ("build_digest", "sha256:tampered_build_digest"),
            ("input_id", "sha256:tampered_input_digest"),
            ("view_map_hash", "9" * 64),
            ("model_hash", "8" * 64),
            ("model_config_hash", "7" * 64),
            ("detector_config_hash", "6" * 64),
            ("seed", 43),
            ("malware_score", 0.913),
            ("signals", {"m1": 0.16, "m2": 0.25, "m3": 0.35, "m4": 0.45, "m5": 0.55}),
            ("fusion_score", 0.726),
            ("threshold_id", "THRESH-TAMPERED"),
            ("decision", "QUARANTINE"),
            ("latency_ms", {"end_to_end": 8.6}),
        ]

        for field_name, tampered_val in tamper_cases:
            data = _base_golden_dict()
            data[field_name] = tampered_val
            tampered_ev = CanonicalEvidence.from_dict(data)

            # Recomputed hash must differ from original
            assert tampered_ev.compute_hash() != original_hash, f"Hash collision on tampered {field_name}!"

            # Verifying against original hash MUST fail
            with pytest.raises(EvidenceIntegrityError, match="Evidence hash mismatch"):
                tampered_ev.verify_integrity(original_hash)

            # If tampered object keeps original expected hash in evidence_hash, it fails
            tampered_with_fake_hash = CanonicalEvidence(
                **{**tampered_ev.__dict__, "evidence_hash": original_hash}
            )
            with pytest.raises(EvidenceIntegrityError, match="Evidence hash mismatch"):
                tampered_with_fake_hash.verify_integrity()

    def test_verify_integrity_missing_hash_raises_error(self) -> None:
        ev = CanonicalEvidence.from_dict(_base_golden_dict())
        assert ev.evidence_hash is None

        with pytest.raises(EvidenceIntegrityError, match="No evidence_hash stored and no expected_hash provided"):
            ev.verify_integrity()
