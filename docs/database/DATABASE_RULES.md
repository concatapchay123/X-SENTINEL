# DATABASE RULES — mandatory for humans and AI coding agents

1. Microsoft SQL Server is the canonical operational database.
2. Alembic is the only schema-change mechanism.
3. Never run ad-hoc `ALTER/CREATE/DROP` against a shared environment.
4. Never modify a migration already applied/shared; create a new revision.
5. ORM model change and migration must be in the same task/PR.
6. API/frontend work that depends on a new field must depend on the migration task.
7. CI must pass `alembic upgrade head` and `alembic check` before merge.
8. Backend readiness must fail on migration revision mismatch.
9. Production deploy order is: backup/verify → migration → backend → frontend.
10. Destructive changes require expand/migrate/contract, never one-step drop.
11. Large binaries and raw result bundles are not DB blobs; store URI + SHA-256.
12. Blind-evaluation ground truth must never be placed in the application database.
13. Secrets/passwords are never committed; `.env.example` is placeholder only.
14. Every persistent table needs purpose, owner, retention and test coverage.
15. Rollback must account for data compatibility; code rollback does not imply safe DB downgrade.
