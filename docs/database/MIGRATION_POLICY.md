# Migration Policy

## Create a migration

```bash
alembic -c database/alembic.ini revision --autogenerate -m "describe change"
alembic -c database/alembic.ini upgrade head
alembic -c database/alembic.ini check
```

## Required sequence

`Requirement → DB spec → ORM model → Alembic revision → migration test → API/backend → frontend → E2E`

## Shared environment rule

Once a migration revision has been merged/applied, it is immutable. Fixes are a new migration.

## Destructive changes

Use expand-and-contract:

1. add nullable/new structure;
2. deploy compatible code;
3. backfill;
4. verify;
5. switch reads/writes;
6. later remove old structure in a separate approved migration.

## Migration ownership

Only a task explicitly declaring `Database impact` may change models/migrations.
