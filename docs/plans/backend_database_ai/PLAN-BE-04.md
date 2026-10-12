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
