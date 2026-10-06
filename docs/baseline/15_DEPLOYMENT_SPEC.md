# 15 — DEVOPS / DEPLOYMENT / OBSERVABILITY

## Environments

- `development`: demo mode allowed.
- `test`: deterministic fixtures, no external state.
- `staging`: demo mode OFF, frozen candidate config/model, acceptance runs.
- `production`: only after acceptance/sign-off.

## Containers

- backend FastAPI container, non-root.
- frontend Streamlit container, non-root.
- config mounted read-only.
- artifacts mounted writable.
- models mounted read-only.

## CI quality gates

1. Python syntax/import check.
2. Ruff.
3. Mypy.
4. Pytest.
5. Build Docker images.
6. Contract smoke test.
7. Security/dependency scan `[PROPOSED]`.

## Observability

- structured application logs.
- audit JSONL separate from diagnostic logs.
- request ID propagated end-to-end.
- health/readiness endpoints.
- latency timings recorded in evidence.

## Rollback

Rollback uses a complete release tuple:

`code image digest + model hash + config hash + view-map hash + detector config hash`.

Never roll back code without its compatible config/model bundle.

## V2 deploy order

`backup/restore readiness → SQL Server healthy → migrate to head → schema guard → backend ready → frontend ready`.

Code rollback must verify DB compatibility; never blindly downgrade a schema containing production data.
