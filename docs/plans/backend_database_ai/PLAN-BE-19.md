# PLAN-BE-19 — Raw PE/LIEF Phase 2

## Objective
Enable static raw PE ingestion only after equivalence and safety gates.

## Status: TECHNICAL IMPLEMENTATION & SAFETY VERIFICATION PASS (PRODUCTION ACTIVATION FAIL-CLOSED GATED)

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/data/raw_pe.py`
- `backend/src/x_sentinel/data/__init__.py`
- `tests/fixtures/synthetic_pe.py`
- `backend/tests/test_raw_pe_no_execution.py`
- `backend/tests/test_raw_pe_malformed.py`
- `backend/tests/test_raw_pe_equivalence.py`
- `tests/security/test_raw_pe_disabled.py`
- `docs/reviews/BE-19_PREREQUISITE_REPORT.md`
- `docs/reviews/BE-19_SECURITY_TEST_REPORT.md`
- `docs/reviews/BE-19_FEATURE_EQUIVALENCE_REPORT.md`
- `docs/reviews/BE-19_ACCEPTANCE_REPORT.md`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-04 PASS verified with 49 tests; Extractor Equivalence Gate evaluated and audited).
2. [x] Freeze interfaces/config/schema for this slice (`RawPEFeatureExtractor`, `validate_input_path`, `read_bounded_bytes`, `validate_pe_structure`, `extract_static_pe`, typed error classes).
3. [x] Implement or update skeleton/code/docs (`raw_pe.py`, `data/__init__.py`, `tests/fixtures/synthetic_pe.py`, reports in `docs/reviews/`).
4. [x] Add positive and negative tests (50 raw PE tests across no-execution, malformed resilience, exact equivalence, and baseline gating).
5. [x] Produce evidence/artifact hashes where applicable (audit reports, exact 2,381 feature group breakdown, X_test.dat vectorization equivalence verified).
6. [x] Update traceability/readiness.

## Acceptance
- [x] **no execution test**: 5 tests in `backend/tests/test_raw_pe_no_execution.py` PASS (AST audit bans execution calls; runtime mocks verify zero process execution; read-only file enforcement).
- [x] **malformed PE test**: 30 tests in `backend/tests/test_raw_pe_malformed.py` PASS (13 structural variants, empty bytes, truncated headers, section bounds, oversized limits, path traversal with and without base_dir, bit-flip fuzzing fail-closed without crashing).
- [x] **feature equivalence**: 14 tests in `backend/tests/test_raw_pe_equivalence.py` PASS (2,381 canonical dimensions, 9 feature groups, determinism, view mapping split, EMBER2018 JSONL row 0-9 vectorization match to X_test.dat with max abs diff = 0.0, exact StringExtractor bit-exact match with max abs diff = 0.0, exact scalar hashing for binary=None, LIEF 1.0 vs 0.9 drift audit documented).

## Prerequisite Gate Decision
- **BE-04**: PASS.
- **Extractor Equivalence Gate**: PREREQUISITE NO-GO for production activation due to LIEF 1.0 vs 0.9 / NumPy 2.x breaking differences in legacy EMBER package and lack of raw PE corpus in repository.
- **Production API (`POST /v1/analyze/file`)**: Remains safely gated (HTTP 501 `XS_FEATURE_DISABLED`).
- **Baseline Default**: `RawPEFeatureExtractor()` remains fail-closed (`FeatureGatedError` / `NotImplementedError`).

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`BE-20` (Acceptance, Evidence Pack & Handover).
