# X-SENTINEL V3 — OPERATIONS & RUNTIME RUNBOOK
## System Administration, Deployment, Detector Operations, Jev AI & Incident Protocols

> **Target Version:** v0.3.0  
> **Repository Commit:** Git HEAD (`99797ff`)  
> **Audience:** Site Reliability Engineers, System Administrators, Security Operations Center (SOC) Analysts  

---

### 1. System Prerequisites & Environment Setup

#### Supported Operating Systems
- Ubuntu 22.04 LTS / Debian 12 (Recommended for Production Containers).
- Windows Server 2022 / Windows 10/11 64-bit (Supported for local development & evaluation).

#### Hardware Sizing Guidelines
| Deployment Tier | CPU | Memory | Disk Storage | Target Concurrent Workload |
|---|---|---|---|---|
| **Minimal / Evaluation** | 4 cores | 8 GB RAM | 20 GB SSD | 1–5 req/sec (Vector-only) |
| **Operational Standard** | 8 cores | 16 GB RAM | 50 GB NVMe | 10–25 req/sec (With TreeSHAP) |
| **High-Throughput Cluster** | 16 cores | 32 GB RAM | 100 GB NVMe | 50+ req/sec (Multi-worker) |

#### Environment Variables Configuration
Copy `.env.example` to `.env` and configure operational parameters:

```ini
# Application Core
XS_ENV=production
XS_LOG_LEVEL=INFO
XS_HOST=0.0.0.0
XS_PORT=8000

# Microsoft SQL Server Database
XS_DB_DIALECT=mssql
XS_DB_HOST=sqlserver
XS_DB_PORT=1433
XS_DB_NAME=xsentinel_v3
XS_DB_USER=xs_app_user
XS_DB_PASSWORD=<STRONG_INJECTED_PASSWORD>

# Authoritative Detector Science
XS_DETECTOR_CONFIG_PATH=configs/detector.yaml
XS_VIEW_MAP_PATH=configs/views.demo.yaml
XS_MODEL_CONFIG_PATH=configs/model.ember2018.yaml
XS_CALIBRATION_PATH=artifacts/calibration/d1_calibration.json
XS_ALLOW_DEMO_MODE=false

# Jev AI Collaboration Layer (Local Advisory Only)
XS_JEV_AI_ENABLED=true
XS_JEV_AI_BASE_URL=http://localhost:1234/v1
XS_JEV_AI_MODEL=jev-style-qwen3.5-2b-decision@q8_0
XS_JEV_AI_ADVISORY_ONLY=true
XS_JEV_AI_CONNECT_TIMEOUT_SEC=2.0
XS_JEV_AI_READ_TIMEOUT_SEC=15.0

# Security & RBAC
XS_API_AUTH_MODE=bearer
XS_JWT_SECRET=<STRONG_INJECTED_SECRET>
```

---

### 2. Starting the Backend Services

#### Local Process Startup (Development / Single-Node)

```bash
# Validate database connection and schema head
python scripts/ensure_database.py
python scripts/check_schema_revision.py

# Start FastAPI application via Uvicorn
uvicorn x_sentinel.main:app --host 0.0.0.0 --port 8000 --workers 2
```

#### Docker Compose Multi-Container Startup

```bash
# Pre-flight compose file validation
docker compose config

# Build and start services in detached mode
docker compose up -d --build

# Verify container health and logs
docker compose ps
docker compose logs -f backend
```

#### Health and Readiness Verification

```bash
# Liveness probe (verifies FastAPI runtime responsiveness)
curl -s http://localhost:8000/health | jq .

# Readiness probe (verifies database schema convergence and model readiness)
curl -s http://localhost:8000/ready | jq .

# Jev AI operational status probe
curl -s http://localhost:8000/v1/ai/status | jq .
```

*Success Criteria*:
- `/health` returns `200 OK` with `status: "healthy"`.
- `/ready` returns `200 OK` with `status: "ready"` and `db_status: "current"`.
- `/v1/ai/status` returns `status: "ready"` (or `status: "disabled"` if AI is turned off).

---

### 3. Core Detector Operations

#### Vector Inference Workflow (`POST /v1/analyze/vector`)

The detector accepts pre-extracted 2,381-dimensional EMBER feature vectors:

```bash
curl -X POST http://localhost:8000/v1/analyze/vector \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <AUTH_TOKEN>" \
  -d '{
    "request_id": "req-20261015-001",
    "features": [0.012, 0.45, ... 2381 floats ...],
    "metadata": {
      "filename": "sample_eval.exe",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  }'
```

*Response Breakdown*:
- `decision`: Canonical authoritative verdict (`pass`, `alert`, `quarantine`).
- `fusion_score`: Bounded fusion anomaly score $\in [0.0, 1.0]$.
- `malware_score`: Base LightGBM classifier prediction.
- `signals`: Complete vector of individual detector scores (`m1_tadr`, `m2_strip`, `m3_view`, `m4_cross_view`, `m5_semantic`).
- `evidence_hash`: Deterministic SHA-256 digest of immutable canonical evidence record.

#### Retrieving Immutable Evidence (`GET /v1/analysis/{id}/evidence`)

```bash
curl -s http://localhost:8000/v1/analysis/req-20261015-001/evidence \
  -H "Authorization: Bearer <AUTH_TOKEN>" | jq .
```

*Integrity Check*: The API verifies the cryptographic SHA-256 hash against the persisted record on read. Any bit-flip tampering triggers HTTP 409 (`XS_EVIDENCE_INTEGRITY_MISMATCH`).

#### Handling Raw PE Uploads (`POST /v1/analyze/file`)
Raw PE binary ingestion remains **FAIL-CLOSED GATED** (HTTP 501 `XS_FEATURE_DISABLED`). Operators must not bypass this gate until Phase 2 LIEF extractor equivalence is approved.

---

### 4. Jev AI Collaborative Workflows

#### Operating Modes
1. **Disabled Mode (`XS_JEV_AI_ENABLED=false`)**:
   - Zero outbound HTTP socket connections to LM Studio.
   - Explain and Report endpoints gracefully fall back to deterministic templates.
   - Backend `/ready` probe is never blocked.
2. **Enabled Mode (`XS_JEV_AI_ENABLED=true`)**:
   - Outbound connections restricted strictly to configured loopback endpoint (`XS_JEV_AI_BASE_URL`).
   - All executions are `advisory_only: true`.

#### Executing Explain Workflow (`POST /v1/ai/explain`)

```bash
curl -X POST http://localhost:8000/v1/ai/explain \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <AUTH_TOKEN>" \
  -d '{
    "analysis_id": "req-20261015-001",
    "question": "Summarize contributing factors for quarantine verdict"
  }'
```

#### Capturing Analyst Feedback (`POST /v1/ai/runs/{run_id}/feedback`)

```bash
curl -X POST http://localhost:8000/v1/ai/runs/run-xyz-123/feedback \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <AUTH_TOKEN>" \
  -d '{
    "rating": 5,
    "label": "helpful",
    "comment": "Accurately highlighted section header entropy mismatch"
  }'
```

---

### 5. Database Administration & Migration Procedures

#### Pre-flight Migration Gate
Before applying schema migrations, execute the automated migration gate:

```bash
python scripts/migration_gate.py --preflight-only
```

#### Applying Migrations Safely
```bash
# Apply pending Alembic revisions to upgrade head
alembic upgrade head

# Verify post-migration schema integrity and zero drift
python scripts/check_schema_revision.py
python scripts/check_schema_drift.py
```

*Rollback Command*:
```bash
alembic downgrade -1
```

---

### 6. Observability, Telemetry & Monitoring

- **Prometheus Metrics**: Exposed at `/metrics` with counters for total requests, detector latencies, Jev AI timeouts, and database connection pool utilization.
- **Latency Percentiles**: Telemetry tracker maintains circular sample buffers calculating real-time P50, P95, and P99 latency percentiles.
- **Audit Log Ingestion**: Structured JSON lines in `artifacts/audit/events.jsonl` should be forwarded to SIEM / Splunk / Elastic via FluentBit.

---

### 7. Security Incident Response Protocols

#### Scenario 1: Detected Evidence Tampering (HTTP 409)
1. Immediately isolate the affected analysis job ID.
2. Extract the persisted database record and compare SHA-256 against the audit log entry in `artifacts/audit/events.jsonl`.
3. If database record differs from append-only audit event, initiate database audit investigation and revoke write credentials.

#### Scenario 2: Suspected Blind Custody Contamination
1. If evaluation ground-truth or trigger manifest files are discovered in application database or detector logs:
   - Immediately suspend active evaluation runs.
   - Execute `python scripts/scan_secrets.py --path .` and `pytest tests/security/test_be16_security_deep_audit.py`.
   - Quarantine contaminated database snapshots.
   - Re-evaluate blind datasets using isolated fresh seeds and keys.

#### Scenario 3: LM Studio / Jev AI Denial of Service
1. If Jev AI response times exceed 15s or error rates spike:
   - Temporarily set `XS_JEV_AI_ENABLED=false`.
   - Core detector pipeline continues processing at full speed without degradation.
   - Restart local LM Studio server and verify model memory residency before re-enabling.
