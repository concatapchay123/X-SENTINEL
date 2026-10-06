# 07 — DATABASE SPEC — V3

## Decision

**Microsoft SQL Server (MSSQL)** is the canonical relational database for the multi-user product baseline. Alembic is the only schema-change mechanism.

Canonical migration head: `0002_v3_jev_ai_audit`.  
Dialect: `mssql+pyodbc` with Windows Authentication (`Trusted_Connection=yes`) or SQL Server Authentication (`sa`).

## Core entities

- `users`, `roles`, `user_roles`
- `model_versions`
- `analysis_jobs`, `analysis_results`, `detector_scores`
- `alerts`, `artifacts`, `audit_events`
- `experiment_runs`

## SQL Server Type Mappings

- Identifiers: `uniqueidentifier` (mapped to `sa.Uuid()`).
- Booleans: `bit` (`1`/`0`, mapped to `sa.Boolean()`).
- Timestamps: `datetimeoffset` with UTC (mapped to `sa.DateTime(timezone=True)`).
- JSON payloads: `nvarchar(max)` (mapped to `sa.JSON()` with native `ISJSON`/`JSON_VALUE` support in SQL Server 2016+).

## V3 Jev AI entities

### `jev_ai_runs`

Purpose: audit each local AI invocation without making AI output part of the canonical detector result.

Required fields:

- `id` UUID / uniqueidentifier PK
- `analysis_job_id` nullable FK -> `analysis_jobs`
- `requested_by_user_id` nullable FK -> `users`
- `mode` (`explain`, `triage`, `compare`, `report`, `docs`)
- `status` (`queued`, `running`, `completed`, `failed`, `blocked`)
- `model_id` nvarchar(255)
- `endpoint_label` nvarchar(120), default `lm_studio_local`
- `prompt_version` nvarchar(120)
- `input_digest_sha256` varchar(64)
- `output_digest_sha256` varchar(64) nullable
- `context_summary` JSON, minimized metadata only
- `response_text` nvarchar(max) nullable and retention-controlled
- `latency_ms` float
- `error_code`, `error_message`
- `created_at`, `completed_at` datetimeoffset

### `jev_ai_feedback`

Purpose: capture analyst feedback without changing detector truth.

- `id` UUID / uniqueidentifier PK
- `jev_ai_run_id` FK -> `jev_ai_runs`
- `user_id` nullable FK -> `users`
- `rating` integer 1..5 nullable
- `label` (`helpful`, `not_helpful`, `incorrect`, `unsafe`, `unclear`) nullable
- `comment` nvarchar(max) nullable
- `created_at` datetimeoffset

## Retention rules

- Prefer hashes + structured metadata.
- Raw prompt/response retention is configurable.
- Do not store raw PE bytes in Jev tables.
- Do not store blind ground truth/trigger labels in Jev tables.
- Sensitive input excerpts should be redacted before persistence.

## Concurrency

- Jev AI runs are append-oriented.
- Detector result transaction must not depend on Jev completion.
- A Jev failure must never roll back a completed `analysis_result`.
- Isolation: SQL Server default `READ COMMITTED` or `READ_COMMITTED_SNAPSHOT` enabled for non-blocking reads.

## Migration rules

- ORM change requires migration.
- Shared migrations are immutable.
- CI runs `upgrade head`, drift checks and DB model tests.
- Backend `/ready` requires the expected migration head.

## Blind boundary

Blind-evaluation manifest, trigger placement and hidden labels remain outside the application DB and are never included in Jev AI context.
