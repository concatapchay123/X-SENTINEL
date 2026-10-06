# X-SENTINEL V3 — Master Plan

## Track A: Backend / Database / AI

| ID | Plan | Depends on |
|---|---|---|
| BE-01 | Repository, environment, config | — |
| BE-02 | SQL Server V3 schema/migrations | BE-01 |
| BE-03 | Backend foundation/readiness | BE-01, BE-02 |
| BE-04 | Domain, input schema, 3-view mapping | BE-03 |
| BE-05 | LightGBM + SHAP service | BE-04 |
| BE-06 | M1–M5 detector core | BE-05 |
| BE-07 | Fusion, D0/D1 calibration, decision | BE-06 |
| BE-08 | Audit/evidence/artifacts | BE-02, BE-07 |
| BE-09 | Core API/history/alerts | BE-03, BE-08 |
| BE-10 | Jev LM Studio client/runtime | BE-03 |
| BE-11 | Jev context/data contract | BE-08, BE-10 |
| BE-12 | Jev orchestration/guardrails | BE-11 |
| BE-13 | Jev persistence/API/feedback | BE-02, BE-12 |
| BE-14 | Threat simulation/E0–E5/metrics | BE-07, BE-08 |
| BE-15 | Security/RBAC/blind isolation | BE-02, BE-09, BE-13 |
| BE-16 | Backend/integration testing | BE-09, BE-13 |
| BE-17 | Performance/observability | BE-09, BE-13 |
| BE-18 | Docker/CI/deployment | BE-16, BE-17 |
| BE-19 | Raw PE/LIEF Phase 2 | BE-04, equivalence gate |
| BE-20 | Acceptance/evidence/handover | BE-14…19 |

## Track B: Frontend

| ID | Plan | Depends on |
|---|---|---|
| FE-01 | Frontend foundation/navigation | API schemas stable |
| FE-02 | API client/state/errors | BE-09 contract |
| FE-03 | Analyze workflow | FE-02 |
| FE-04 | Result dashboard | FE-03 |
| FE-05 | SHAP/cross-view visualizations | FE-04 |
| FE-06 | Jev AI advisory UI | BE-13 + FE-02 |
| FE-07 | History/alerts/evidence | BE-09 + FE-02 |
| FE-08 | Status/evaluation/admin | BE-09/14/15 |
| FE-09 | UX/security/accessibility | FE-03…08 |
| FE-10 | Frontend E2E/acceptance | FE-09 + BE-18 |

## Milestone view

### M0 — Baseline frozen
Docs, V3 migration, API schemas, Jev role/guardrails approved.

### M1 — Canonical detector usable
Vector -> LightGBM/SHAP -> M1–M5 -> fusion -> persistent result.

### M2 — Operator product usable
Analyze/result/history/status UI with evidence export.

### M3 — Jev AI collaborator usable
Local LM Studio explain/triage/report with audit and failure isolation.

### M4 — Research evidence complete
E0–E5, metrics, blind protocol and reproducible evidence pack.

### M5 — Production acceptance candidate
Security/RBAC, performance, deployment, backup/restore and E2E gates.
