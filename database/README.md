# X-SENTINEL Database — V3

Microsoft SQL Server (MSSQL) + Alembic is canonical. Current migration head: `0002_v3_jev_ai_audit`.

- `0001_v2_multiuser`: core product persistence (users, roles, model versions, analysis jobs, results, scores, alerts, artifacts, audit events, experiments).
- `0002_v3_jev_ai_audit`: optional Jev AI run and feedback audit tables (`jev_ai_runs`, `jev_ai_feedback`).

Jev AI tables store advisory metadata only. They do not replace or mutate canonical `analysis_results`.

Use migrations (`alembic -c database/alembic.ini upgrade head`); do not apply `database/schema/schema.sql` manually in normal development.
