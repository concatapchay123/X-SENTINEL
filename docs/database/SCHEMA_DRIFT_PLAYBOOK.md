# Schema Drift Playbook

Symptoms: one developer works while another gets missing-column/table/type errors.

1. Stop feature debugging.
2. Compare repo commit and `alembic heads`.
3. Run `make db-status`.
4. Confirm current DB revision equals repository head.
5. If behind: run `make db-migrate`.
6. If ahead/unknown: do **not** edit DB manually; identify the migration branch/commit.
7. If ORM differs from migration: run `make db-check`; create/repair a migration before feature work continues.
8. Never solve drift by deleting migration files or changing `alembic_version` manually.

For disposable local development only, `docker compose down -v` may recreate data from zero. Never use that procedure for shared/staging/production data.
