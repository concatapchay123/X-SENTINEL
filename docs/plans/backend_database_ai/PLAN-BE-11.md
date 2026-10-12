# PLAN-BE-11 — Jev AI Context Builder & Data Contract

## Objective
Project canonical evidence through an allowlist, redact, cap and digest.

## Status: PASS

## Scope

- Define and implement canonical data contract projection for Jev AI collaboration layer.
- Enforce authoritative allowlist with default-deny semantics across all top-level and nested structures.
- Implement recursive sensitive data redaction for authentication tokens, API keys, credentials, database connection strings, and private user paths without mutating input evidence.
- Isolate blind evaluation data (ground truth labels, holdout manifests, backdoor trigger definitions) with strict fail-closed rejection.
- Enforce canonical context size cap (character ceiling) over deterministic RFC 8785 JSON representation.
- Compute reproducible context digest (SHA-256) over canonical serialized payload.
- Maintain detector science, platform persistence, and Jev AI authority boundaries explicit (advisory-only, zero influence on detector decisions, immutable canonical evidence).
- Provide end-to-end compatibility with BE-08 `CanonicalEvidence`, BE-09 history/evidence services, and BE-10 `JevAIClient` / `JevAIOrchestrator`.

## Primary files
- `backend/src/x_sentinel/jev_ai/prompt_builder.py`
- `backend/src/x_sentinel/jev_ai/guardrails.py`
- `backend/src/x_sentinel/jev_ai/__init__.py`
- `backend/tests/test_be11_context_builder.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 through BE-10 verified; BE-10 status PASS).
2. [x] Freeze interfaces/config/schema for this slice (`ALLOWED_CONTEXT_KEYS`, `FORBIDDEN_KEYS`, `BLIND_DATA_KEYS`, `apply_allowlist`, `redact_sensitive_data`, `validate_context`, `project_canonical_evidence`, `build_safe_context`, `build_messages`, `compute_context_digest`).
3. [x] Implement context builder, authoritative allowlist projection, sensitive data redaction, blind data isolation, size cap, canonicalization, and digest in `guardrails.py`, `prompt_builder.py`, and `__init__.py`.
4. [x] Add positive and negative tests (101 comprehensive automated tests in `backend/tests/test_be11_context_builder.py`).
5. [x] Verify evidence hashing integrity, deterministic RFC 8785 JSON representation, and SHA-256 digests.
6. [x] Verify regression across foundational backend test suite (547 passed tests with zero regressions).
7. [x] Update traceability/readiness documentation (`PLAN-BE-11.md`).

## Acceptance

### 1. Forbidden key tests: PASS
- Explicit denylist and recursive key traversal (`walk_keys`) block any forbidden keys across all nested levels:
  - Raw PE/binary: `raw_pe`, `raw_binary`, `raw_bytes`, `pe_bytes`, `file_bytes`, `binary_data`, `byte_stream`.
  - Raw feature vector: `features`, `feature_vector`, `raw_features`, `vector`, `full_vector`, `raw_vector`, `feature_array`.
  - Credentials & Secrets: `api_key`, `secret`, `password`, `passwd`, `pwd`, `token`, `auth_token`, `access_token`, `database_url`, `db_password`, `private_key`, `client_secret`.
  - User PII & Filesystem: `user_data`, `personal_data`, `pii`, `credit_card`, `ssn`, `filesystem_path`, `arbitrary_file`.
- Blocks forbidden keys at top level, deeply nested dictionaries, lists of dictionaries, and case variations (`RAW_PE`, `Api_Key`, `PASSWORD`).
- Authoritative allowlist projection (`apply_allowlist`) enforces default-deny: unknown keys are discarded by default, or rejected in strict mode with `JevAllowlistViolation`.
- Verified by tests: `TestForbiddenKeysEnforcement` (11 tests / 40+ parameterized variations).

### 2. Size cap tests: PASS
- Configured maximum size ceiling (`max_context_chars`, default 30,000) enforced over deterministic RFC 8785 JSON representation.
- Payloads exceeding limit immediately raise `JevContextSizeExceeded` (subclass of `JevContextBlocked`).
- Exact boundary tested: context at `exact_size` passes; context at `exact_size - 1` fails.
- Oversized nested dictionaries, oversized warning lists, and multi-byte Unicode content (Vietnamese diacritics, Japanese characters, emojis) correctly measured without character truncation artifacts.
- JSON escaping expansion accurately captured in canonical string measurement.
- Verified by tests: `TestSizeCapEnforcement` (9 tests).

### 3. Blind-data negative tests: PASS
- Synthetic blind evaluation fixtures strictly isolated:
  - Evaluation ground truth: `blind_label`, `ground_truth`, `true_label`, `eval_label`, `target_label`, `blind_ground_truth`, `hidden_label`.
  - Backdoor triggers & manifests: `trigger_manifest`, `hidden_manifest`, `poison_manifest`, `backdoor_manifest`, `blind_manifest`.
- Blind markers detected and blocked at top level, in nested diagnostics, in feature lists, and in free-form operator text questions (`check_blind_data_in_text`).
- Outgoing payload inspection with mock HTTP transport formally verifies zero blind data reaches LM Studio runtime.
- Verified by tests: `TestBlindDataIsolation` (19 tests / 12 parameterized variations).

## Extended Verification & Architectural Invariants

- **Sensitive Data Redaction**: Recursive regex redaction sanitizes Bearer tokens, API keys, passwords, database URLs, and Windows/Linux user profile paths (`redact_sensitive_data`, `redact_sensitive_text`).
- **Input Immutability**: Verified that `CanonicalEvidence` and input dictionaries are never mutated during projection, redaction, or digest calculation (`test_redaction_does_not_mutate_input_object`, `test_project_canonical_evidence_from_dataclass`).
- **Deterministic Digest**: Reproducible SHA-256 digest computed over RFC 8785 canonical JSON representation (`compute_context_digest`, `test_canonical_json_sorting_and_separators`, `test_golden_reference_digest`).
- **Detector Independence**: Verified that canonical detector truth (`decision`, `malware_score`, `signals` M1–M5) is preserved with zero modification, and system prompt strictly enforces advisory-only boundaries (`test_detector_truth_unmodified_by_ai_pipeline`).
- **End-to-End Orchestrator Integration**: Verified full compatibility with `JevAIOrchestrator.run()` and `JevAIClient` (`test_end_to_end_orchestrator_pipeline_with_projected_context`).

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`PLAN-BE-12` (Jev AI Orchestration & Guardrails).
