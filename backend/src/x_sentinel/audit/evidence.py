from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any


class EvidenceError(Exception):
    """Base exception for evidence contract violations."""


class EvidenceValidationError(EvidenceError):
    """Raised when evidence fails canonical schema validation."""


class EvidenceIntegrityError(EvidenceError):
    """Raised when evidence hash mismatch or tampering is detected."""


class EvidenceImmutabilityError(EvidenceError):
    """Raised when an attempt is made to mutate finalized immutable evidence."""


class ScientificEvidenceRejectedError(EvidenceError):
    """Raised when demo-mode output is submitted as scientific evidence."""


CANONICAL_DECISIONS = frozenset({"PASS", "ALERT", "QUARANTINE"})
ALLOWED_DECISIONS = CANONICAL_DECISIONS | {"DEMO_ONLY"}
REQUIRED_SIGNAL_KEYS = frozenset({"m1", "m2", "m3", "m4", "m5"})
ALLOWED_INPUT_MODES = frozenset({"vector", "raw_pe"})


def _is_finite_float(val: Any) -> bool:
    return isinstance(val, (int, float)) and not math.isnan(val) and not math.isinf(val)


@dataclass(frozen=True)
class CanonicalEvidence:
    """Immutable canonical detector evidence adhering to 27_EVIDENCE_SCHEMA.md.

    Every non-demo acceptance analysis includes exactly these 19 canonical fields.
    Acceptance scripts reject demo_mode=True as scientific evidence.
    """

    request_id: str
    run_id: str
    timestamp: str
    code_commit: str
    build_digest: str
    input_id: str
    input_mode: str
    view_map_hash: str
    model_hash: str
    model_config_hash: str
    detector_config_hash: str
    seed: int
    malware_score: float
    signals: dict[str, float]
    fusion_score: float
    threshold_id: str
    decision: str
    latency_ms: dict[str, float]
    demo_mode: bool
    evidence_hash: str | None = None

    def __post_init__(self) -> None:
        # Validate required string identities
        for field_name in (
            "request_id",
            "run_id",
            "timestamp",
            "code_commit",
            "build_digest",
            "input_id",
            "view_map_hash",
            "model_hash",
            "model_config_hash",
            "detector_config_hash",
            "threshold_id",
        ):
            val = getattr(self, field_name)
            if not isinstance(val, str) or not val.strip():
                raise EvidenceValidationError(
                    f"Field '{field_name}' must be a non-empty string, got {val!r}"
                )

        # Validate timestamp format (ISO 8601)
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except Exception as exc:
            raise EvidenceValidationError(
                f"Timestamp '{self.timestamp}' is not a valid ISO 8601 format: {exc}"
            ) from exc

        # Validate input_mode
        if self.input_mode not in ALLOWED_INPUT_MODES:
            raise EvidenceValidationError(
                f"input_mode must be one of {sorted(ALLOWED_INPUT_MODES)}, got {self.input_mode!r}"
            )

        # Validate seed
        if not isinstance(self.seed, int):
            raise EvidenceValidationError(f"seed must be an integer, got {self.seed!r}")

        # Validate malware_score
        if not _is_finite_float(self.malware_score) or not (0.0 <= self.malware_score <= 1.0):
            raise EvidenceValidationError(
                f"malware_score must be a finite float in [0.0, 1.0], got {self.malware_score!r}"
            )

        # Validate fusion_score
        if not _is_finite_float(self.fusion_score) or not (0.0 <= self.fusion_score <= 1.0):
            raise EvidenceValidationError(
                f"fusion_score must be a finite float in [0.0, 1.0], got {self.fusion_score!r}"
            )

        # Validate signals (must have m1..m5)
        if not isinstance(self.signals, dict):
            raise EvidenceValidationError(f"signals must be a dict, got {type(self.signals).__name__}")
        if set(self.signals.keys()) != REQUIRED_SIGNAL_KEYS:
            raise EvidenceValidationError(
                f"signals must contain exactly keys {sorted(REQUIRED_SIGNAL_KEYS)}, got {sorted(self.signals.keys())}"
            )
        for sig_name, sig_val in self.signals.items():
            if not _is_finite_float(sig_val) or not (0.0 <= sig_val <= 1.0):
                raise EvidenceValidationError(
                    f"signals['{sig_name}'] must be a finite float in [0.0, 1.0], got {sig_val!r}"
                )

        # Validate decision
        if self.decision not in ALLOWED_DECISIONS:
            raise EvidenceValidationError(
                f"decision must be one of {sorted(ALLOWED_DECISIONS)}, got {self.decision!r}"
            )

        # Validate latency_ms
        if not isinstance(self.latency_ms, dict):
            raise EvidenceValidationError(f"latency_ms must be a dict, got {type(self.latency_ms).__name__}")
        if "end_to_end" not in self.latency_ms:
            raise EvidenceValidationError("latency_ms must include 'end_to_end' key")
        for lat_k, lat_v in self.latency_ms.items():
            if not _is_finite_float(lat_v) or lat_v < 0.0:
                raise EvidenceValidationError(
                    f"latency_ms['{lat_k}'] must be a non-negative finite float, got {lat_v!r}"
                )

        # Validate demo_mode
        if not isinstance(self.demo_mode, bool):
            raise EvidenceValidationError(f"demo_mode must be a boolean, got {self.demo_mode!r}")

        # Validate evidence_hash format if present
        if self.evidence_hash is not None:
            if not isinstance(self.evidence_hash, str) or len(self.evidence_hash) != 64:
                raise EvidenceValidationError(
                    f"evidence_hash must be a 64-character hex string, got {self.evidence_hash!r}"
                )
            try:
                int(self.evidence_hash, 16)
            except ValueError as exc:
                raise EvidenceValidationError(
                    f"evidence_hash must be hexadecimal, got {self.evidence_hash!r}"
                ) from exc

    def validate_for_scientific_acceptance(self) -> None:
        """Enforces scientific acceptance rule: reject demo_mode=True and non-canonical decisions."""
        if self.demo_mode:
            raise ScientificEvidenceRejectedError(
                "Acceptance scripts must reject demo_mode=true as scientific evidence per 27_EVIDENCE_SCHEMA.md"
            )
        if self.decision not in CANONICAL_DECISIONS:
            raise ScientificEvidenceRejectedError(
                f"Canonical scientific decision must be one of {sorted(CANONICAL_DECISIONS)}, got {self.decision!r}"
            )

    def to_canonical_dict(self) -> dict[str, Any]:
        """Returns the dictionary of the 19 canonical fields without evidence_hash."""
        return {
            "build_digest": self.build_digest,
            "code_commit": self.code_commit,
            "decision": self.decision,
            "demo_mode": self.demo_mode,
            "detector_config_hash": self.detector_config_hash,
            "fusion_score": float(self.fusion_score),
            "input_id": self.input_id,
            "input_mode": self.input_mode,
            "latency_ms": {k: float(v) for k, v in sorted(self.latency_ms.items())},
            "malware_score": float(self.malware_score),
            "model_config_hash": self.model_config_hash,
            "model_hash": self.model_hash,
            "request_id": self.request_id,
            "run_id": self.run_id,
            "seed": self.seed,
            "signals": {k: float(v) for k, v in sorted(self.signals.items())},
            "threshold_id": self.threshold_id,
            "timestamp": self.timestamp,
            "view_map_hash": self.view_map_hash,
        }

    def to_canonical_json(self) -> str:
        """Deterministic canonical JSON serialization (RFC 8785 / JCS compatible)."""
        return json.dumps(self.to_canonical_dict(), sort_keys=True, separators=(",", ":"))

    def compute_hash(self) -> str:
        """Computes the SHA-256 digest over the canonical JSON representation."""
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    def with_hash(self) -> CanonicalEvidence:
        """Returns a new CanonicalEvidence instance with evidence_hash bound."""
        computed = self.compute_hash()
        return CanonicalEvidence(
            request_id=self.request_id,
            run_id=self.run_id,
            timestamp=self.timestamp,
            code_commit=self.code_commit,
            build_digest=self.build_digest,
            input_id=self.input_id,
            input_mode=self.input_mode,
            view_map_hash=self.view_map_hash,
            model_hash=self.model_hash,
            model_config_hash=self.model_config_hash,
            detector_config_hash=self.detector_config_hash,
            seed=self.seed,
            malware_score=self.malware_score,
            signals=dict(self.signals),
            fusion_score=self.fusion_score,
            threshold_id=self.threshold_id,
            decision=self.decision,
            latency_ms=dict(self.latency_ms),
            demo_mode=self.demo_mode,
            evidence_hash=computed,
        )

    def verify_integrity(self, expected_hash: str | None = None) -> bool:
        """Verifies evidence integrity against its computed SHA-256 digest."""
        computed = self.compute_hash()
        target = expected_hash or self.evidence_hash
        if target is None:
            raise EvidenceIntegrityError("No evidence_hash stored and no expected_hash provided.")
        if computed != target:
            raise EvidenceIntegrityError(
                f"Evidence hash mismatch! Computed {computed}, expected {target}."
            )
        return True

    def to_dict(self) -> dict[str, Any]:
        """Returns all fields including evidence_hash if set."""
        d = self.to_canonical_dict()
        if self.evidence_hash is not None:
            d["evidence_hash"] = self.evidence_hash
        return d

    def to_json(self, indent: int = 2) -> str:
        """Returns formatted JSON representation."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CanonicalEvidence:
        """Instantiates CanonicalEvidence from dictionary."""
        if not isinstance(data, dict):
            raise EvidenceValidationError(f"Expected dict, got {type(data).__name__}")
        
        required_keys = {
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
        }
        missing = required_keys - set(data.keys())
        if missing:
            raise EvidenceValidationError(f"Missing required fields: {sorted(missing)}")

        return cls(
            request_id=data["request_id"],
            run_id=data["run_id"],
            timestamp=data["timestamp"],
            code_commit=data["code_commit"],
            build_digest=data["build_digest"],
            input_id=data["input_id"],
            input_mode=data["input_mode"],
            view_map_hash=data["view_map_hash"],
            model_hash=data["model_hash"],
            model_config_hash=data["model_config_hash"],
            detector_config_hash=data["detector_config_hash"],
            seed=data["seed"],
            malware_score=float(data["malware_score"]),
            signals={k: float(v) for k, v in data["signals"].items()},
            fusion_score=float(data["fusion_score"]),
            threshold_id=data["threshold_id"],
            decision=data["decision"],
            latency_ms={k: float(v) for k, v in data["latency_ms"].items()},
            demo_mode=bool(data["demo_mode"]),
            evidence_hash=data.get("evidence_hash"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> CanonicalEvidence:
        """Parses JSON string into CanonicalEvidence."""
        try:
            data = json.loads(json_str)
        except Exception as exc:
            raise EvidenceValidationError(f"Malformed JSON: {exc}") from exc
        return cls.from_dict(data)


def compute_evidence_hash(evidence_data: CanonicalEvidence | dict[str, Any]) -> str:
    """Computes SHA-256 for a CanonicalEvidence instance or raw dictionary."""
    if isinstance(evidence_data, CanonicalEvidence):
        return evidence_data.compute_hash()
    evidence = CanonicalEvidence.from_dict(evidence_data)
    return evidence.compute_hash()


def verify_evidence_hash(
    evidence_data: CanonicalEvidence | dict[str, Any],
    expected_hash: str | None = None,
) -> bool:
    """Verifies evidence hash integrity."""
    if isinstance(evidence_data, CanonicalEvidence):
        return evidence_data.verify_integrity(expected_hash)
    evidence = CanonicalEvidence.from_dict(evidence_data)
    return evidence.verify_integrity(expected_hash)
