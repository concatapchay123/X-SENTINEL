# PLAN-BE-20 — Acceptance, Evidence Pack & Handover

## Objective
Run SE/SC gates, Jev operational acceptance and package reproducible handover.

## Status: COMPLETE (CONDITIONAL GO / EXPERIMENTAL READY)

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `docs/handover/`
- `artifacts/`
- `SHA256SUMS.txt`
- `scripts/verify_scientific_reproducibility.py`
- `scripts/generate_sha256sums.py`
- `scripts/verify_sha256sums.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 through BE-19 audited; blockers OQ-01, OQ-02, and MISSING_POISONED_MODELS transparently isolated).
2. [x] Freeze interfaces/config/schema for this slice (`SHA256SUMS.txt`, Handover Package layout, Release Tuple).
3. [x] Implement or update skeleton/code/docs (12 handover documents created under `docs/handover/`, verification scripts added).
4. [x] Add positive and negative tests (Negative checksum tampering tests, E0–E5 metric recomputation, full 993-test regression suite).
5. [x] Produce evidence/artifact hashes where applicable (Full cryptographic SHA-256 manifest generated and verified).
6. [x] Update traceability/readiness (Traceability matrix, SE/SC matrices, release checklist 10/10 PASS).

## Acceptance
- [x] **acceptance checklist**: Formally verified across BE-01..BE-19 in `docs/handover/BE01_BE19_ACCEPTANCE_MATRIX.md` and SE-01..05 / SC-01..05 in `docs/handover/SE_SC_ACCEPTANCE_MATRIX.md`.
- [x] **checksums**: Formally generated and verified in `SHA256SUMS.txt` via `scripts/generate_sha256sums.py` and `scripts/verify_sha256sums.py` with 0 mismatches and negative tests PASS.
- [x] **runbook**: Formally published with validated commands in `docs/handover/OPERATIONS_RUNBOOK.md` and `docs/handover/ROLLBACK_RUNBOOK.md`.
- [x] **known limitations**: Formally cataloged without whitewashing in `docs/handover/KNOWN_LIMITATIONS.md` and `docs/handover/RISK_REGISTER.md`.

## Done definition

No silent TBDs, no undocumented schema/API changes, 993/993 tests pass (100% green), outputs are traceable to versioned config/code, and formal sign-off checklist is prepared in `docs/handover/SIGNOFF_CHECKLIST.md`.
