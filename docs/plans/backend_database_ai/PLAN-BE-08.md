# PLAN-BE-08 — Audit, Evidence & Artifact Contracts

## Objective
Persist immutable canonical evidence and artifact checksums.

## Status: PASS

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit (Zero runtime AI/LLM dependencies).
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/audit/__init__.py`
- `backend/src/x_sentinel/audit/evidence.py`
- `backend/src/x_sentinel/audit/artifacts.py`
- `backend/src/x_sentinel/audit/writer.py`
- `backend/src/x_sentinel/audit/manager.py`
- `backend/src/x_sentinel/database/repositories/__init__.py`
- `backend/src/x_sentinel/database/repositories/analysis.py`
- `backend/src/x_sentinel/database/repositories/detector.py`
- `backend/src/x_sentinel/database/repositories/artifact.py`
- `backend/src/x_sentinel/database/repositories/audit_event.py`
- `backend/src/x_sentinel/database/repositories/evidence.py`
- `docs/baseline/27_EVIDENCE_SCHEMA.md`
- `backend/tests/test_be08_canonical_evidence_contract.py`
- `backend/tests/test_be08_evidence_immutability.py`
- `backend/tests/test_be08_evidence_hashing_integrity.py`
- `backend/tests/test_be08_artifact_contracts.py`
- `backend/tests/test_be08_repositories.py`
- `backend/tests/test_be08_audit_write_failure.py`
- `backend/tests/test_be08_end_to_end_integration.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 through BE-07 all PASS; 337 baseline tests verified).
2. [x] Freeze interfaces/config/schema for this slice (`CanonicalEvidence`, `ArtifactRecord`, `AuditWriter`, `AuditEvidenceManager`, `AnalysisJobRepository`, `AnalysisResultRepository`, `DetectorScoreRepository`, `ArtifactRepository`, `AuditEventRepository`, `CanonicalEvidenceRepository`).
3. [x] Implement or update skeleton/code/docs (`evidence.py`, `artifacts.py`, `writer.py`, `manager.py`, `analysis.py`, `detector.py`, `artifact.py`, `audit_event.py`, `evidence.py`).
4. [x] Add positive, negative, integrity, immutability, and failure injection tests (46 targeted tests across 7 test modules, 383 passed across full repo suite).
5. [x] Produce evidence/artifact hashes where applicable (frozen reference evidence SHA-256: `994e7f813be6702d9d4def0d93edc47ff4dc1fd5249af19e65768d106a59594e`).
6. [x] Update traceability and readiness documentation (`PLAN-BE-08.md`, `17_TRACEABILITY_MATRIX.md`, `18_FEATURE_MATRIX.md`, `24_BASELINE_READINESS_REPORT.md`).

## Acceptance
- [x] audit write failure test:
  - Database commit failure injection: verified session rollback, zero orphan records in DB, and explicit `AuditWriteFailureError` propagation.
  - Live Microsoft SQL Server rollback verification on injected connection drop.
  - File-based append audit write failure: verified explicit `AuditWriteFailureError` propagation when disk/directory is unwritable.
  - Zero false persistence acknowledgement: errors are never swallowed.
  - Scientific truth preservation: detector numerical outputs (`malware_score`, `signals`, `fusion_score`, `decision`) remain untouched after write failures.
  - Zero Jev AI involvement: verified zero external network or AI calls during persistence failure handling.
  - 6 passed tests in `test_be08_audit_write_failure.py`.
- [x] evidence hash test:
  - Deterministic SHA-256 digest calculation over canonical JSON serialization (RFC 8785 / JCS compatible: sorted keys, compact separators `(',', ':')`, UTF-8).
  - Key insertion order invariance verified.
  - Frozen golden reference hash verified: `994e7f813be6702d9d4def0d93edc47ff4dc1fd5249af19e65768d106a59594e`.
  - Tampering detection verified across all 19 canonical fields (`request_id`, `run_id`, `timestamp`, `code_commit`, `build_digest`, `input_id`, `view_map_hash`, `model_hash`, `model_config_hash`, `detector_config_hash`, `seed`, `malware_score`, `signals`, `fusion_score`, `threshold_id`, `decision`, `latency_ms`).
  - Strict rejection of `demo_mode=true` for scientific acceptance per `27_EVIDENCE_SCHEMA.md` (`ScientificEvidenceRejectedError`).
  - 5 passed tests in `test_be08_evidence_hashing_integrity.py`.
- [x] canonical evidence contract:
  - 19 canonical fields validation, bounds checking, finite numeric verification, signal keys contract (`m1`..`m5`), ISO 8601 UTC timestamp format validation.
  - 14 passed tests in `test_be08_canonical_evidence_contract.py`.
- [x] evidence immutability:
  - In-place mutation forbidden via frozen dataclass contract; dictionary decoupling verified.
  - 3 passed tests in `test_be08_evidence_immutability.py`.
- [x] artifact contracts & checksums:
  - Streaming SHA-256 calculation, checksum mismatch detection (`ArtifactIntegrityError`), missing file handling (`ArtifactNotFoundError`), directory traversal prevention (`ArtifactSecurityError`).
  - 8 passed tests in `test_be08_artifact_contracts.py`.
- [x] database repositories:
  - `AnalysisJobRepository`, `AnalysisResultRepository`, `DetectorScoreRepository`, `ArtifactRepository`, `AuditEventRepository` (strictly append-only), `CanonicalEvidenceRepository` (atomic transactional unit-of-work).
  - Integration verified against live Microsoft SQL Server.
  - 8 passed tests in `test_be08_repositories.py`.
- [x] end-to-end integration:
  - Full pipeline verified from `DetectorPipeline` (BE-06) + `FusionEngine` (BE-07) -> `CanonicalEvidence` -> SHA-256 Hashing -> Persistence -> Read-back & Verification.
  - Verified on SQLite and live Microsoft SQL Server.
  - 2 passed tests in `test_be08_end_to_end_integration.py`.

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`BE-09` (Core API, History & Alerts).
