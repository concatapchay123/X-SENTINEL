# PLAN-05 — PostgreSQL Persistence, Migration & Audit Foundation

**Objective:** Establish one canonical multi-user schema and prevent database drift across developers, AI agents and environments.  
**Scope:** PostgreSQL, SQLAlchemy metadata, Alembic, seed, audit metadata, backup/restore skeleton, schema guard.  
**Status:** READY (baseline/skeleton created; live-environment evidence still required).  
**Dependencies:** PLAN-01, PLAN-02, PLAN-03, PLAN-04.  
**Rollback:** code rollback only after checking DB compatibility; destructive schema downgrade is never automatic.

## TASK-05-01 — Run canonical PostgreSQL service
- **Priority:** P0
- **Files:** `docker-compose.yml`, `.env.example`
- **Acceptance:** all developers use the same image/tag/config and persistent named volume.

## TASK-05-02 — Maintain SQLAlchemy canonical metadata
- **Priority:** P0
- **Files:** `backend/src/x_sentinel/database/models.py`
- **Acceptance:** model metadata has deterministic constraints and no hidden ground-truth tables.

## TASK-05-03 — Maintain Alembic migration history
- **Priority:** P0
- **Files:** `database/migrations/**`, `database/alembic.ini`
- **Acceptance:** one Alembic head; `upgrade head` works from empty DB; applied revisions are immutable.

## TASK-05-04 — Enforce schema revision readiness
- **Priority:** P0
- **Files:** `database/health.py`, `scripts/check_schema_revision.py`, `/ready`
- **Acceptance:** backend is BLOCKED when DB revision != expected repo revision.

## TASK-05-05 — Add seed/reference data
- **Priority:** P1
- **Files:** `database/seed/seed_dev.py`
- **Acceptance:** idempotent role seed; no real credentials/secrets.

## TASK-05-06 — Backup/restore and recovery drill
- **Priority:** P1
- **Files:** `database/scripts/backup.sh`, `restore.sh`
- **Acceptance:** backup checksum captured; restore tested in disposable environment before production acceptance.

## TASK-05-07 — Integrate durable repositories
- **Priority:** P0
- **Files:** `backend/src/x_sentinel/database/repositories/**`
- **Acceptance:** services use repository/session boundaries, transactions are explicit, integration tests pass.

## TASK-05-08 — Schema drift CI gate
- **Priority:** P0
- **Files:** `.github/workflows/ci.yml`
- **Acceptance:** CI runs migration, revision check and `alembic check` before tests can pass.

## Definition of Done

PostgreSQL boots; empty DB upgrades to head; schema matches ORM; backend readiness is green; DB roundtrip test passes; no P0 drift issue; backup/restore drill evidence exists for production.
