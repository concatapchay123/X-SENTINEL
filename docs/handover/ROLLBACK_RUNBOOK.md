# X-SENTINEL V3 — SYSTEM ROLLBACK RUNBOOK
## Atomic Release Tuple Recovery, Database Downgrade & Post-Rollback Smoke Verification

> **Target Version:** v0.3.0  
> **Release Bundle Digest:** `sha256:41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb`  
> **Canonical Target Reference:** `docs/baseline/15_DEPLOYMENT_SPEC.md`, `artifacts/release/release_tuple.json`, `docs/runbooks/ROLLBACK_RUNBOOK.md`  

---

### 1. Rollback Trigger Criteria

An emergency rollback must be initiated immediately upon encountering any of the following conditions during deployment or staging:

1. **Migration Gate Failure**: Database schema migration fails to apply cleanly or introduces undetected schema drift.
2. **Detector Truth Incompatibility**: Recomputed inference scores on golden benchmark cases diverge from frozen thresholds.
3. **Evidence Integrity Failure**: Persistent evidence write failures (`AuditWriteFailureError`) or cryptographic verification mismatches.
4. **Container Boot Failure**: Backend container crashes on startup or fails liveness/readiness probes (`/health`, `/ready`).
5. **Security Isolation Breach**: Detection of blind evaluation tokens or credentials in application logs or API responses.

---

### 2. The Atomic Release Tuple

A valid rollback in X-SENTINEL V3 cannot consist solely of reverting a container image. All 6 core components of the **Canonical Release Tuple** must be restored synchronously to maintain mutual compatibility:

```text
+---------------------------------------------------------------------------------+
|                           CANONICAL RELEASE TUPLE                               |
|                                                                                 |
|  1. Container Image Digest   : sha256:7ab139a6c5be6aab8f9f... (UID 10001)       |
|  2. Database Schema Revision : 0002_v3_jev_ai_audit (Alembic single head)       |
|  3. Model Booster Artifact   : sha256:509de4a83e2d76b69fb3... (EMBER2018)      |
|  4. View Mapping Config      : sha256:d0a4fd5c7fd7b3c5a373... (views.demo.yaml) |
|  5. Detector Threshold Config: sha256:78374ea02719aad0d972... (detector.yaml)   |
|  6. Calibration Bundle       : sha256:45bc1eed6edf3c04d4b6... (D1 calib)       |
|                                                                                 |
|  LOCKED UNDER ATOMIC BUNDLE DIGEST:                                             |
|  sha256:41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb       |
+---------------------------------------------------------------------------------+
```

---

### 3. Step-by-Step Rollback Execution

#### Phase 1: Halt Incoming Traffic & Capture State
```bash
# Shift load balancer or reverse proxy traffic away from the affected node
# Ensure running jobs complete (drain connections for 10s)
docker compose stop backend
```

#### Phase 2: Database Schema Reversion (If Applicable)
Before restoring application containers, evaluate whether database schema changes must be rolled back:

```bash
# 1. Check current schema revision in target database
python scripts/check_schema_revision.py

# 2. If rolling back from an unapproved revision to canonical head 0002_v3_jev_ai_audit:
alembic downgrade 0002_v3_jev_ai_audit

# 3. Verify zero schema drift post-downgrade
python scripts/check_schema_drift.py
```

*Data Preservation Guard*: Reverting migrations must NEVER drop `analysis_jobs`, `analysis_results`, `detector_scores`, or `audit_events`. Canonical historical evidence is append-only and strictly preserved.

#### Phase 3: Restore Configuration & Artifact State
```bash
# Restore frozen configuration files from Git or release bundle archive
git checkout tags/v0.3.0 -- configs/
git checkout tags/v0.3.0 -- artifacts/calibration/d1_calibration.json

# Verify cryptographic hashes of restored configurations
python scripts/verify_release_tuple.py --verify-only
```

#### Phase 4: Container Image Reversion
```bash
# Deploy prior verified container image digest from release tuple
export XS_BACKEND_IMAGE="x-sentinel-backend@sha256:7ab139a6c5be6aab8f9f1b5ed4c76b4eb7799fa782a533ae22bb4f143d7c99ff"

# Restart containers with verified image
docker compose up -d backend
```

---

### 4. Post-Rollback Smoke Verification

Following rollback, execute the smoke verification suite to confirm full system operational integrity:

```bash
# 1. Verify service liveness and readiness
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:8000/ready || exit 1

# 2. Verify database connectivity and schema convergence
python scripts/ensure_database.py

# 3. Run automated deployment smoke tests
pytest tests/deployment/test_be18_staging_smoke.py -q

# 4. Verify end-to-end vector inference and evidence generation
pytest backend/tests/test_be08_end_to_end_integration.py -q
```

*Success Declaration*: If all 4 checks return exit code 0, declare system restored to stable operational baseline.
