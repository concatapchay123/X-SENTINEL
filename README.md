# X-SENTINEL V3 — Detection Core + Jev AI Collaborative Analysis

> **Status:** IMPLEMENTATION-READY V3 baseline + runnable V2 detector skeleton preserved.  
> **Architecture rule:** X-SENTINEL Detection Core is authoritative; Jev AI is advisory and must never silently override detector scores, thresholds, labels, quarantine decisions, or scientific evidence.

V3 reorganizes the project into two implementation tracks while preserving the scientific core and the V2 Microsoft SQL Server / Alembic foundation:

1. **Backend / Database / Detection / Jev AI** — canonical data, inference, M1–M5, fusion, persistence, APIs, Jev AI orchestration, security, evaluation and deployment.
2. **Frontend** — operator workflows, analysis/result visualization, Jev AI explanations, alert/history screens, status/admin views and E2E acceptance.

The previous 24 plans are retained under `docs/plans/legacy_v2/` for traceability. V3 plans live under:

- `docs/plans/backend_database_ai/`
- `docs/plans/frontend/`

## V3 target flow

```text
Dataset / EMBER vector (2,381 features)
        |
        v
Schema validation -> 3 semantic views -> LightGBM -> SHAP -> M1..M5
        |                                                |
        +-------------------> Fusion / Calibration <-----+
                                   |
                                   v
                      Pass / Alert / Quarantine
                                   |
                    +--------------+---------------+
                    |                              |
                    v                              v
             SQL Server / Audit               Jev AI Adapter
             canonical evidence               (LM Studio local)
                    |                              |
                    +--------------+---------------+
                                   v
                           FastAPI contracts
                                   |
                                   v
                              Frontend UI
```

## Jev AI role

Jev AI is a **local analysis collaborator**, not a malware classifier and not a scientific oracle. It may:

- explain M1–M5, SHAP and cross-view evidence in operator-friendly language;
- summarize why a sample was flagged;
- compare two analyses or two model/config versions;
- generate analyst triage notes and report drafts from canonical evidence;
- identify contradictions/missing evidence and ask for human review;
- help navigate system documentation and approved runbooks.

Jev AI may **not**:

- change detector thresholds/weights/model files;
- mark an alert safe/malicious as an authoritative decision;
- access blind-evaluation ground truth or hidden trigger manifests;
- execute PE files, shell commands, or arbitrary tools;
- send evidence to a cloud model unless a future ADR explicitly enables it.

See `docs/jev_ai/` and `docs/baseline/28_JEV_AI_SPEC.md` through `31_JEV_AI_OPERATIONAL_GUARDRAILS.md`.

## Dataset policy

The ZIP intentionally contains an **empty `datasets/` directory**. Put EMBER/BODMAS or other locally acquired datasets there after extraction. Dataset files are not included in V3.

Recommended local layout after you add data:

```text
datasets/
├── ember2018/
├── bodmas/
├── calibration_d1/
└── derived/              # generated splits/features; keep out of Git
```

Do not commit datasets. Do not expose blind-evaluation labels to the detector or Jev AI.

## Start order

Read:

1. `docs/baseline/00_PROJECT_BASELINE.md`
2. `docs/baseline/05_ARCHITECTURE.md`
3. `docs/baseline/07_DATABASE_SPEC.md`
4. `docs/baseline/09_BACKEND_SPEC.md`
5. `docs/baseline/10_API_CONTRACT.md`
6. `docs/baseline/11_FRONTEND_SPEC.md`
7. `docs/baseline/13_AI_RAG_SPEC.md`
8. `docs/baseline/28_JEV_AI_SPEC.md`
9. `docs/baseline/29_JEV_AI_DATA_CONTRACT.md`
10. `docs/baseline/30_JEV_AI_INTEGRATION_SPEC.md`
11. `docs/baseline/31_JEV_AI_OPERATIONAL_GUARDRAILS.md`
12. `docs/plans/MASTER_PLAN_V3.md`

## Quick start

```bash
cp .env.example .env
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

Docker:

```bash
docker compose up --build
```

- Backend: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Frontend: `http://localhost:8501`
- LM Studio Jev AI endpoint: configured by `XS_JEV_AI_BASE_URL` and optional by default.

## LM Studio / Jev AI

1. Load the Jev-compatible local model in LM Studio.
2. Start LM Studio's OpenAI-compatible local server.
3. Set `XS_JEV_AI_ENABLED=true`.
4. Set `XS_JEV_AI_BASE_URL`, for example `http://localhost:1234/v1` outside Docker or `http://host.docker.internal:1234/v1` for Docker Desktop.
5. Set `XS_JEV_AI_MODEL` to the exact model identifier shown by LM Studio.
6. Keep `XS_JEV_AI_ADVISORY_ONLY=true`.

The exact Jev model architecture, context window, quantization and license are intentionally **TBD** until the actual model file you use is identified. V3 does not invent those properties.

## Database V3

Canonical migration head: `0002_v3_jev_ai_audit`.

New tables:

- `jev_ai_runs`: one auditable Jev AI invocation tied to an analysis job when applicable.
- `jev_ai_feedback`: optional operator feedback on a Jev AI output.

Jev prompts/responses are recorded only according to the configured retention policy; hashes and structured metadata are preferred over raw sensitive payloads.

## Scientific boundary

A Jev AI explanation is **not scientific evidence** for SC-01…SC-05. Scientific claims must come from frozen detector configurations and experiment outputs. Jev AI may explain or summarize that evidence but cannot create missing evidence.

## V3 deliverables

- V2 runnable detector skeleton preserved.
- Microsoft SQL Server / Alembic V3 persistence design.
- Backend + DB + AI implementation plans.
- Separate Frontend implementation plans.
- Jev AI model/runtime/data/API/security/evaluation specifications.
- Jev AI local client/orchestrator skeleton.
- Empty `datasets/` directory.
- V3 manifest and validation scripts.
