# X-SENTINEL V3 — DEPLOYMENT & RELEASE RUNBOOK

## Document Metadata

- **System:** X-SENTINEL V3 (Cross-View Backdoor Detector with Local Advisory Jev AI)
- **Version:** 0.3.0
- **Canonical Architecture:** Microsoft SQL Server (MSSQL), FastAPI, Streamlit, Docker Compose
- **Target Schema Revision:** `0002_v3_jev_ai_audit`
- **Owner:** Principal DevOps & Site Reliability Engineering (SRE)

---

# 1. PREREQUISITES & ENVIRONMENT CLASSIFICATION

X-SENTINEL V3 recognises four deployment tiers:

| Tier | Purpose | Demo Mode | Database Engine | Jev AI Runtime |
|---|---|---|---|---|
| `development` | Local engineering | Allowed (`true`) | SQL Server / Local SQLExpress | Disabled or Host LM Studio |
| `test` | Deterministic CI/CD | Allowed (`true`) | Containerised MSSQL 2022 | Disabled (Mocked tests) |
| `staging` | Pre-release verification | Prohibited (`false`) | Staging MSSQL 2022 | Local LM Studio host |
| `production` | Authorized production | Prohibited (`false`) | Production MSSQL Cluster | Local LM Studio host |

### Required Host Tools

- Docker Engine 24.0+ / Docker Desktop with containerd store.
- Docker Compose v2.20+.
- Microsoft ODBC Driver 17 or 18 for SQL Server.
- Python 3.11+ with `setuptools`, `alembic`, `sqlalchemy`.
- Git 2.40+.

---

# 2. PRE-DEPLOYMENT VERIFICATION & SECRETS INJECTION

### 2.1. Environment Configuration

Create or verify `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Ensure configuration invariants:

```ini
XS_ENV=staging
XS_DEMO_MODE=false
XS_DATABASE_REQUIRED=true
XS_EXPECTED_DB_REVISION=0002_v3_jev_ai_audit
XS_BACKEND_HOST=0.0.0.0
XS_BACKEND_PORT=8000
XS_JEV_AI_ENABLED=false
XS_JEV_AI_BASE_URL=http://host.docker.internal:1234/v1
XS_JEV_AI_ADVISORY_ONLY=true
XS_JEV_AI_LOCAL_ONLY=true
```

### 2.2. Secret Isolation Rule

1. Secrets (`MSSQL_SA_PASSWORD`, `XS_AUTH_SECRET_KEY`) must **NEVER** be baked into Dockerfile build args or image layers.
2. Secrets are injected at container startup via runtime environment variables or Docker Compose `.env`.
3. Verify zero secrets in working tree before proceeding:

```bash
python scripts/scan_secrets.py --path .
```

---

# 3. DATABASE MIGRATION GATE

Before starting new container images, execute the mandatory **Migration Gate**:

```bash
python scripts/migration_gate.py --upgrade --require-backup
```

### Gate Verifications

1. **Alembic Head:** Validates exactly one single head exists (`0002_v3_jev_ai_audit`).
2. **Dialect Integrity:** Validates Microsoft SQL Server connection and permissions.
3. **Pre-migration Backup:** In staging/production, fails closed unless verified backup is registered (`XS_BACKUP_VERIFIED=true`).
4. **Schema Drift Check:** Verifies all 13 canonical tables exist and zero forbidden tables (`ground_truth`, `manifest`, `blind_labels`) are present.

*If this gate exits with a non-zero code, deployment is immediately aborted.*

---

# 4. CONTAINER IMAGE BUILD & VERIFICATION

### 4.1. Build Deterministic Images

```bash
docker build -f infrastructure/docker/backend.Dockerfile -t x-sentinel-backend:0.3.0 .
docker build -f infrastructure/docker/frontend.Dockerfile -t x-sentinel-frontend:0.3.0 .
```

### 4.2. Verify Runtime Hardening

Ensure non-root execution:

```bash
docker run --rm x-sentinel-backend:0.3.0 whoami
# Expected output: appuser (UID 10001)
```

Ensure native libraries (LightGBM, SHAP, PyODBC) load correctly:

```bash
docker run --rm x-sentinel-backend:0.3.0 python -c "import lightgbm; import shap; import pyodbc; print('OK')"
# Expected output: OK
```

Verify build context exclusion (zero secrets, zero forbidden datasets):

```bash
docker run --rm x-sentinel-backend:0.3.0 ls -la /app
# Verify no .env, no datasets, no private manifests exist in image
```

---

# 5. SERVICE STARTUP & TOPOLOGY

Deploy the complete stack via Docker Compose:

```bash
docker compose up -d
```

### Startup Order

1. `mssql`: Starts Microsoft SQL Server 2022 container, waits for healthy state (SQL test `SELECT 1`).
2. `migrate`: Executes migration preflight and applies Alembic upgrade to head.
3. `backend`: Starts FastAPI application once migrations complete successfully.
4. `frontend`: Starts Streamlit UI once backend reports healthy.

---

# 6. POST-DEPLOYMENT SMOKE TESTS

Execute the automated staging verification:

```bash
# 1. Healthcheck
curl -f http://localhost:8000/health

# 2. Readiness probe (checks DB & detector readiness)
curl -f http://localhost:8000/ready

# 3. Config status
curl -f http://localhost:8000/v1/config/status

# 4. Run staging smoke test suite
pytest tests/deployment/test_be18_staging_smoke.py -v
```

---

# 7. GENERATE CANONICAL RELEASE TUPLE

Record the immutable release tuple:

```bash
python scripts/verify_release_tuple.py
```

This creates:
- `artifacts/release/release_tuple.json`
- `artifacts/release/RELEASE_MANIFEST.md`

Lock this release tuple digest for audit and atomic rollback operations.
