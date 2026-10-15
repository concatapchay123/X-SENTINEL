# X-SENTINEL V3 — ROLLBACK & DISASTER RECOVERY RUNBOOK

## Document Metadata

- **System:** X-SENTINEL V3 (Cross-View Backdoor Detector with Local Advisory Jev AI)
- **Version:** 0.3.0
- **Scope:** Atomic Release Tuple Rollback, Database Preservation, Incident Recovery
- **Owner:** Disaster Recovery & Site Reliability Engineering (SRE)

---

# 1. ROLLBACK CONTRACT & ATOMIC RELEASE TUPLE

In accordance with `docs/baseline/15_DEPLOYMENT_SPEC.md`, rollback in X-SENTINEL V3 operates strictly on the **Complete Release Tuple**:

$$\text{Rollback Tuple} = \langle \text{Image Digest}, \text{Model Hash}, \text{Config Hash}, \text{View-Map Hash}, \text{Detector Config Hash}, \text{DB Revision} \rangle$$

### Cardinal Invariant

**Never roll back an application image in isolation.**  
Rolling back code without its corresponding calibration bundle, threshold configuration, or database revision creates silent classification skew or runtime failures.

---

# 2. ROLLBACK CLASSIFICATION & DECISION MATRIX

| Failure Mode | Trigger Scenario | Recovery Strategy | Database Action |
|---|---|---|---|
| **Class A: Application Crash / Hang** | Container fails readiness probe, runtime unhandled exception | Roll back container image and configs to prior release tuple | None (Schema remains forward-compatible) |
| **Class B: Scientific Incompatibility** | M1–M5 feature mismatch, calibration skew, threshold regression | Re-pin detector config, view-map, and model hash simultaneously | None (Scientific models reside in frozen files) |
| **Class C: Database Migration Failure** | DDL migration error, schema corruption, lock exhaustion | Abort rollout; restore database from pre-migration backup snapshot | **Database Restore** (Requires explicit SRE approval) |
| **Class D: Jev AI Local Outage** | Host LM Studio unavailable, model timeout | Jev AI is **advisory only**. Do not roll back detector. Set `XS_JEV_AI_ENABLED=false` | None |

---

# 3. DATABASE RECOVERY SAFETY RULES

1. **NEVER blindly execute `alembic downgrade` on a database with production/staging data:**
   - DDL downgrade operations may drop columns containing persistent analysis jobs, audit events, or Jev AI runs.
   - If the candidate release did not introduce breaking table changes, keep the existing database schema and simply roll back the application container.
2. **When Database Restore is Mandatory:**
   - If a corrupted migration partially applied non-transactional changes, restore the isolated database from the verified pre-migration backup point.
   - Document any writes that occurred between rollout and restore for audit reconciliation.

---

# 4. STEP-BY-STEP ROLLBACK PROCEDURE

### Step 1: Identify Target Prior Release Tuple

Inspect the verified release ledger in `artifacts/release/release_tuple.json` (or version control tags):

```bash
python scripts/verify_release_tuple.py --verify-only
```

Note the verified prior digest (e.g. `sha256:target_digest`).

### Step 2: Halt Current Services

Gracefully terminate the candidate deployment:

```bash
docker compose down
```

### Step 3: Re-pin Configuration and Model Artifacts

Ensure configuration files are restored to the exact hashes defined in the target release tuple:

```bash
git checkout <PREVIOUS_RELEASE_TAG> -- configs/ models/
```

### Step 4: Verify Database Schema Compatibility

Run the migration gate in validation mode against the target release revision:

```bash
python scripts/migration_gate.py --expected-revision 0002_v3_jev_ai_audit
```

*If database schema matches the expected revision, proceed to Step 5.*

### Step 5: Start Previous Service Containers

Start the stack with the target image version:

```bash
# If using versioned image tags:
docker compose -f docker-compose.yml up -d
```

### Step 6: Verify Recovery & Health

Verify that all service health and readiness probes respond with 200 OK:

```bash
# Health probe
curl -f http://localhost:8000/health

# Readiness probe
curl -f http://localhost:8000/ready

# Config status
curl -f http://localhost:8000/v1/config/status
```

### Step 7: Run Regression Verification

Execute the automated release verification suite:

```bash
python scripts/release_gate.py --skip-tests
pytest tests/deployment/test_be18_release_tuple_rollback.py -v
```

---

# 5. POST-INCIDENT AUDIT & LOG RETENTION

1. Export container logs from the failed deployment:
   ```bash
   docker logs <failed_container_id> > artifacts/audit/rollback_incident_$(date +%s).log
   ```
2. Verify that canonical evidence in `artifacts/audit/events.jsonl` was not corrupted.
3. Record root cause analysis (RCA) in `docs/plans/backend_database_ai/PLAN-BE-18.md`.
