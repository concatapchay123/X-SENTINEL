# 00 — PROJECT BASELINE / CONSTITUTION — V3

## Purpose

X-SENTINEL is a per-file inference-time defensive system intended to identify suspicious inputs that may carry backdoor trigger patterns using static EMBER features and cross-view semantic consistency signals. V3 adds **Jev AI**, a local advisory collaborator that explains and analyzes canonical detector evidence without becoming part of the detector decision path.

The execution strategy remains **Product first, evidence first, report second**.

## Non-negotiable principles

1. Evidence before claims. A design, mockup, placeholder, target or AI narrative is not an actual experimental result.
2. Detection Core must not use hidden manifest/ground truth at inference time.
3. Research/MVP mode consumes pre-vectorized EMBER rows; do not invoke PE extraction on vectors.
4. Raw PE parsing is a separate static-only adapter and cannot be treated as equivalent until mapping tests pass.
5. No malware execution, detonation, payload activation or binary modification.
6. Scientific thresholds/configs must be frozen before blind testing.
7. Every important result must be reproducible from versioned config + seed + input identity + code revision.
8. Frontend renders backend evidence and does not invent detector logic.
9. API/database changes are contract/migration first.
10. Architectural change requires change control.
11. **Detector result is authoritative; Jev AI output is advisory only.**
12. Jev AI cannot read blind ground truth/hidden trigger manifests, execute binaries/tools, or silently call cloud AI.
13. Jev AI outage/failure must not invalidate or roll back a canonical detector result.
14. The distributed package contains an empty `datasets/` directory; datasets are locally supplied by the user.

## Status vocabulary

| Status | Meaning |
|---|---|
| EXISTING | Supported by supplied X-SENTINEL material |
| PARTIAL | Spec exists; implementation/evidence incomplete |
| PROPOSED | Baseline decision introduced to unblock implementation |
| TBD | Must be resolved; no silent assumption |
| N/A | Deliberately not used |

## Source-of-truth order

1. `00_PROJECT_BASELINE.md`
2. `02_REQUIREMENTS.md`
3. `03_SCOPE.md`
4. `05_ARCHITECTURE.md`
5. `07_DATABASE_SPEC.md`
6. `09_BACKEND_SPEC.md`
7. `10_API_CONTRACT.md`
8. `11_FRONTEND_SPEC.md`
9. `12_SECURITY_SPEC.md`
10. `13_AI_RAG_SPEC.md`
11. `28_JEV_AI_SPEC.md` → `31_JEV_AI_OPERATIONAL_GUARDRAILS.md`
12. `14_TEST_STRATEGY.md`
13. `docs/plans/MASTER_PLAN_V3.md`
14. approved ADR/change requests
15. source code
16. legacy V2 plans (historical only)

## Product gates

### Gate A — Foundation
Repo/config/schema/API skeleton/DB migration/test/Docker baseline.

### Gate B — Scientific core
M1–M5 canonicalized; model/view map/fusion/calibration frozen.

### Gate C — Operator product
Analyze/result/history/status/evidence UI works against backend contracts.

### Gate D — Jev AI collaboration
Exact local model identified; LM Studio integration, guardrails, audit and failure isolation verified.

### Gate E — Research evaluation
E0–E5 + blind protocol + statistics + immutable evidence.

### Gate F — Production acceptance
SE/SC gates, security/RBAC, performance, backup/restore and E2E evidence.

## Canonical IDs

- Requirements: `FR-*`, `NFR-*`, `SEC-*`, `OPS-*`, `AI-*`
- Backend plans: `BE-01..BE-20`
- Frontend plans: `FE-01..FE-10`
- Legacy plans: `PLAN-01..PLAN-24`
- Tests: `TC-*`, plus `UT/IT/API/E2E/SEC/PERF/AI-*`
- ADR: `ADR-###`
- Change: `CR-###`

## Definition of Done

A feature is DONE only when requirement, architecture, implementation, data/persistence impact, failure handling, security controls, tests, docs, traceability and acceptance evidence are updated. UI alone or AI prose alone is never DONE.
