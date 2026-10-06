# V3 Package Manifest

This package is a V3 planning/specification + runnable skeleton distribution.

## Required major areas

| Area | Location | Status |
|---|---|---|
| Dataset placeholder | `datasets/` | EMPTY BY DESIGN |
| Detector backend | `backend/src/x_sentinel/` | inherited V2 skeleton |
| Jev AI backend adapter | `backend/src/x_sentinel/jev_ai/` | V3 skeleton |
| Database | `database/` | V3 migration/spec |
| Frontend | `frontend/` | V2 runnable + V3 plan |
| Baseline specs | `docs/baseline/` | V3 updated |
| Backend/DB/AI plans | `docs/plans/backend_database_ai/` | V3 |
| Frontend plans | `docs/plans/frontend/` | V3 |
| Jev AI deep specs | `docs/jev_ai/` | V3 |
| Legacy plan traceability | `docs/plans/legacy_v2/` | preserved |

## Source-of-truth precedence

1. `docs/baseline/*`
2. approved ADRs
3. `docs/plans/MASTER_PLAN_V3.md`
4. track-specific plans
5. source code
6. legacy V2 plans (historical reference only)

If a legacy plan conflicts with V3, V3 baseline wins.
