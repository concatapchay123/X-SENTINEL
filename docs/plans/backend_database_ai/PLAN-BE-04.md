# PLAN-BE-04 — Domain, Input Schema & Semantic Views

## Objective
Validate 2,381 features and authoritative Structural/Behavioral/Metadata mapping.

## Status: PASS

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/data/__init__.py`
- `backend/src/x_sentinel/data/schema.py`
- `backend/src/x_sentinel/data/views.py`
- `configs/views.demo.yaml`
- `configs/views.scientific.yaml`
- `backend/tests/test_be04_domain_schema_views.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 PASS, BE-02 PASS, BE-03 PASS verified; OQ-01 tracked and guarded by fail-closed enforcement).
2. [x] Freeze interfaces/config/schema for this slice (`validate_vector`, `validate_vector_batch`, `validate_named_features`, `VectorSchema`, `SliceSpec`, `IndicesSpec`, `ViewMap`, `compute_mapping_hash`, `load_view_map`).
3. [x] Implement or update skeleton/code/docs (`schema.py`, `views.py`, `__init__.py`, `configs/views.demo.yaml`, `configs/views.scientific.yaml`).
4. [x] Add positive and negative tests (49 targeted tests in `test_be04_domain_schema_views.py`, 53 tests in data test suite, 130 passed across full repo suite).
5. [x] Produce evidence/artifact hashes where applicable (canonical demo mapping SHA-256: `276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb`).
6. [x] Update traceability/readiness.

## Acceptance
- [x] schema tests (`backend/tests/test_be04_domain_schema_views.py` and `test_schema.py` PASS: 2,381 exact count, shape, ordering, finite float bounds, non-numeric and boolean rejection, batch validation, named feature dictionary reconstruction).
- [x] view mapping hash test (`backend/tests/test_be04_domain_schema_views.py` and `test_views.py` PASS: deterministic SHA-256 fingerprint verified against `configs/views.demo.yaml`; index mutation detection verified; mathematical bounds and disjoint/completeness integrity verified; scientific mode fail-closed verification on TBD/unresolved map).

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`BE-05` (LightGBM & SHAP Model Service).


## Current Implementation Status

- **Verified Implementation Status:** `COMPLETED_WITH_LIMITATIONS` (Demo Mode Verified / Strict Scientific Mode Fail-Closed Gated)
- **Exact Source File Paths:**
  - `backend/src/x_sentinel/data/schema.py`
  - `backend/src/x_sentinel/data/views.py`
  - `configs/views.demo.yaml`
  - `configs/views.scientific.yaml`
- **Associated Test Suites:**
  - `backend/tests/test_be04_domain_schema_views.py` (49 passed across schema and views)
  - `backend/tests/test_schema.py`
  - `backend/tests/test_views.py`
- **Empirical Artifacts:**
  - `configs/views.demo.yaml` (SHA-256 `d0a4fd5c...`)
  - `configs/views.scientific.yaml`
- **Operational Boundaries & Verified Limitations:**
  - `OQ-01` scientific blocker: `configs/views.scientific.yaml` retains `TBD_MUST_FREEZE_BEFORE_SCIENTIFIC_RUN`. Strict scientific mode fails closed (`ExperimentBlockedError`) by design; system operates reliably in demo mode using `configs/views.demo.yaml`.
