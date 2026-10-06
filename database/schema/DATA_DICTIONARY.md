# X-SENTINEL V3 Data Dictionary (Microsoft SQL Server)

Schema revision: `0002_v3_jev_ai_audit`.  
Canonical RDBMS: Microsoft SQL Server (2019 / 2022 / 2025 / Azure SQL).

## Data Types Mapping (SQL Server)
- **UUID / Identifiers**: `uniqueidentifier` (RFC 4122 GUID).
- **Booleans**: `bit` (`1` = True, `0` = False).
- **Strings**: `nvarchar(N)` (Unicode support).
- **Timestamps**: `datetimeoffset` (ISO 8601 UTC timezone-aware).
- **JSON / Payloads**: `nvarchar(max)` with native JSON validations / functions (`ISJSON`, `JSON_VALUE`).
- **Floating point**: `float` (64-bit IEEE 754).
- **Large Binary pointers**: External URI + SHA-256 hash.

---

## 1. Identity & Access Control

### `users`
Purpose: stable identity record for durable multi-user ownership and audit attribution.

| Column | Type | Null | Key / Rule |
|---|---|---:|---|
| id | uniqueidentifier | no | PK |
| email | nvarchar(320) | no | display/original email |
| normalized_email | nvarchar(320) | no | UNIQUE; lowercase normalized |
| display_name | nvarchar(200) | yes | optional |
| is_active | bit | no | default 1 |
| created_at | datetimeoffset | no | sysdatetimeoffset() |
| updated_at | datetimeoffset | no | sysdatetimeoffset() |

### `roles`
Purpose: canonical role catalog (`admin`, `analyst`, `evaluator`).

| Column | Type | Null | Key / Rule |
|---|---|---:|---|
| id | int | no | PK, IDENTITY(1,1) |
| code | nvarchar(64) | no | UNIQUE |
| description | nvarchar(255) | yes | role description |

### `user_roles`
Purpose: many-to-many RBAC assignment. Composite PK `(user_id, role_id)`.

---

## 2. Model & Analysis Lifecycle

### `model_versions`
Purpose: bind every durable analysis to an identifiable model/config artifact. Unique `(name, version)`; stores SHA-256 and config hash.

| Column | Type | Null | Key / Rule |
|---|---|---:|---|
| id | uniqueidentifier | no | PK |
| name | nvarchar(120) | no | model identifier |
| version | nvarchar(120) | no | version string |
| sha256 | varchar(64) | no | model artifact hash |
| config_hash | varchar(64) | no | config hash |
| metadata_json | nvarchar(max) | no | JSON metadata, default N'{}' |
| is_active | bit | no | default 0 |
| created_at | datetimeoffset | no | sysdatetimeoffset() |

### `analysis_jobs`
Purpose: durable lifecycle of each submitted analysis.
Important rules:
- `request_id` is unique for idempotency/traceability.
- `status` constraint: `queued`, `running`, `completed`, `failed`, `quarantined`.
- `input_mode` constraint: `vector`, `raw_pe`.
- Raw binaries stay outside SQL Server; database stores hash + artifact URI.

### `analysis_results`
Purpose: one canonical final result per analysis job.
Stores final scores (`malware_score`, `suspicion_score`, `threshold`), decision (`pass`, `alert`, `quarantine`), latency, view contributions (JSON) and evidence URI.

### `detector_scores`
Purpose: normalized M1–M5 score rows. Composite PK `(analysis_job_id, detector_code)` prevents duplicates per detector/job.
Constrained to `M1`, `M2`, `M3`, `M4`, `M5`.

### `alerts`
Purpose: SOC alert lifecycle and resolution state. Constrained severities (`low`, `medium`, `high`, `critical`) and statuses (`open`, `acknowledged`, `resolved`, `dismissed`).

---

## 3. Evidence, Audits & Experiments

### `artifacts`
Purpose: metadata pointer to external evidence/model/export objects. Stores URI, SHA-256, MIME type, size and metadata. Large binary content remains in artifact store outside SQL Server.

### `audit_events`
Purpose: structured durable audit trail. Bigint auto-increment PK (`IDENTITY(1,1)`). Append-only; application writes cannot mutate historical records.

### `experiment_runs`
Purpose: E0–E5 run metadata, config hash, seed and result URI. **No hidden ground-truth labels or blind manifests may be stored here.**

---

## 4. Jev AI Local Collaboration (V3 Track)

### `jev_ai_runs`
Purpose: audit each local LM Studio invocation without making AI prose part of the canonical detector result.

| Column | Type | Null | Key / Rule |
|---|---|---:|---|
| id | uniqueidentifier | no | PK |
| analysis_job_id | uniqueidentifier | yes | FK -> analysis_jobs(id) |
| requested_by_user_id | uniqueidentifier | yes | FK -> users(id) |
| mode | nvarchar(32) | no | `explain`, `triage`, `compare`, `report`, `docs` |
| status | nvarchar(32) | no | `queued`, `running`, `completed`, `failed`, `blocked` |
| model_id | nvarchar(255) | no | LM Studio model identifier |
| endpoint_label | nvarchar(120) | no | default `lm_studio_local` |
| prompt_version | nvarchar(120) | no | e.g. `jev-v3.0.0` |
| input_digest_sha256 | varchar(64) | no | SHA-256 of sanitized prompt/context |
| output_digest_sha256 | varchar(64) | yes | SHA-256 of generated output |
| context_summary | nvarchar(max) | no | minimized JSON metadata |
| response_text | nvarchar(max) | yes | retention-controlled output |
| latency_ms | float | yes | execution latency |
| error_code | nvarchar(128) | yes | error category |
| error_message | nvarchar(max) | yes | error details |
| created_at | datetimeoffset | no | sysdatetimeoffset() |
| completed_at | datetimeoffset | yes | completion timestamp |

### `jev_ai_feedback`
Purpose: capture analyst feedback without altering detector truth.
Fields: `id`, `jev_ai_run_id`, `user_id`, `rating` (1..5), `label` (`helpful`, `not_helpful`, `incorrect`, `unsafe`, `unclear`), `comment`, `created_at`.

---

## 5. Index Strategy
Indexes cover:
- Unique constraints: `users(normalized_email)`, `roles(code)`, `model_versions(name, version)`, `analysis_jobs(request_id)`.
- Foreign key lookups and queries: `analysis_jobs(user_id, created_at)`, `artifacts(analysis_job_id, kind)`, `audit_events(entity_type, entity_id)`, `jev_ai_runs(analysis_job_id, created_at)`.
