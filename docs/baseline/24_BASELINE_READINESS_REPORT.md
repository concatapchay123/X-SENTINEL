# 24 — BASELINE READINESS REPORT — V3

## Overall

**PLAN BE-01 (REPOSITORY, ENVIRONMENT & CONFIGURATION) PASS.**  
**PLAN BE-02 (MICROSOFT SQL SERVER V3 SCHEMA & MIGRATION) PASS.**  
**PLAN BE-03 (FASTAPI FOUNDATION, HEALTH & READINESS) PASS.**  
**PLAN BE-04 (DOMAIN, INPUT SCHEMA & SEMANTIC VIEWS) PASS.**  
**PLAN BE-05 (LIGHTGBM & SHAP MODEL SERVICE) PASS.**  
**PLAN BE-06 (M1–M5 DETECTOR CORE) PASS.**  
**PLAN BE-07 (FUSION, D0/D1 CALIBRATION & DECISION) PASS.**  
**PLAN BE-08 (AUDIT, EVIDENCE & ARTIFACT CONTRACTS) PASS.**  
**PLAN BE-09 (CORE API, HISTORY & ALERTS) PASS.**  
**READY FOR JEV AI LM STUDIO RUNTIME CLIENT (BE-10).**  
**NOT YET SCIENTIFICALLY ACCEPTED.**

| Area | Status | Start blocker? | Final acceptance blocker? |
|---|---|---:|---:|
| Repository / Environment / Config (BE-01) | COMPLETE PASS | No | No |
| Microsoft SQL Server / Migrations (BE-02) | COMPLETE PASS | No | backup/load/RBAC evidence |
| Backend Foundation / Readiness (BE-03) | COMPLETE PASS | No | No |
| Requirements | COMPLETE V3 | No | No |
| Architecture | COMPLETE V3 | No | actual integration evidence |
| Detection core | COMPLETE PASS (BE-06 frozen core) | No | BE-07 fusion + E0–E5 evidence |
| Backend API | COMPLETE PASS (BE-09 Core API) | No | contract/integration tests |
| Frontend | PARTIAL runnable Streamlit | No | E2E/UX evidence |
| Jev AI spec | COMPLETE baseline | No | real model ID + integration/evaluation evidence |
| Jev AI runtime | SKELETON | No | endpoint/model tests if feature enabled |
| Security | PARTIAL (BE-09 Auth tested) | No local | auth, secrets, retention, threat tests |
| Deployment | PARTIAL | No | staging/rollback/load evidence |

## BE-01 Milestone Verification

- Repository layout: frozen and audit-passing (20 core files, 20 BE plans, 10 FE plans, 24 legacy plans).
- Dataset policy: `.gitignore` and `.dockerignore` enforce dataset exclusion; `datasets/.gitkeep` preserved; local working copy datasets (`bodmas`, `ember2018`) preserved intact without deletion.
- Environment & configuration: `.env.example`, `configs/jev_ai.yaml`, and `x_sentinel.config.Settings` synchronized and validated.
- Automated tests: 23 passed, 2 skipped (live DB integration).

## BE-02 Milestone Verification

- Canonical migration head: `0002_v3_jev_ai_audit` frozen and verified across Alembic, SQLAlchemy models, and `schema.sql`.
- V3 Jev AI audit schema: `jev_ai_runs` and `jev_ai_feedback` implemented with audit metadata, check constraints (`mode`, `status`, `rating`, `label`), indexes, and foreign keys (`analysis_job_id` ON DELETE SET NULL to preserve audit trail, `jev_ai_run_id` ON DELETE CASCADE).
- Scientific isolation & authority: zero detector fields in Jev tables; zero Jev fields in detector tables; simulated Jev failure does not corrupt or roll back canonical analysis results; blind evaluation ground truth strictly forbidden and absent from schema.
- Upgrade / downgrade verification: verified via offline SQL generation (`0001:0002` and `0002:0001`) and full live database migration cycle on an isolated scratch database (`xsentinel_migration_cycle_test`).
- Schema drift verification: `scripts/check_schema_drift.py` confirmed 0 differences between Alembic, SQLAlchemy `Base.metadata`, and live SQL Server database.
- Automated tests: 40 passed across all test suites with live database.

## BE-03 Milestone Verification

- FastAPI foundation: FastAPI application bootstrapped, mounts CORS middleware, error handlers, and canonical routes (`/health`, `/ready`, `/v1/config/status`, `/v1/ai/status`, `/v1/analyze/vector`).
- Health endpoint: `GET /health` verified responding with liveness metadata (`status: "ok"`), independent of database connectivity or Jev AI / LM Studio availability.
- Database revision readiness: `database_health` in `x_sentinel.database.health` inspects connectivity and Alembic `alembic_version` state; accurately distinguishes `current`, `behind`, `ahead`, `unmigrated`, `unknown`, and `unavailable`. `GET /ready` returns 503 on database unavailability or migration revision mismatch in a read-only manner without executing schema mutations.
- Jev AI status isolation: When disabled (`XS_JEV_AI_ENABLED=false`), zero network calls are made to LM Studio; `GET /v1/ai/status` returns `status: "disabled"`; Jev status never blocks detector readiness. When enabled, probes local endpoint with safe timeout, reports `available`, `unavailable`, or `misconfigured` without blocking detector readiness.
- Security: Zero database credentials, passwords, raw connection strings, or stack traces exposed in `/health`, `/ready`, `/v1/config/status`, or `/v1/ai/status`.
- Automated tests: 22 targeted tests in `test_be03_foundation_health_readiness.py`, 60 passed across full test suite (2 skipped for unconfigured live DB).

## BE-04 Milestone Verification

- Canonical vector schema: exactly 2,381 features enforced; ordering preserved; strict finite numeric bounds; booleans, strings, bytes, None, and nested shapes rejected; batch validation and named feature dictionary reconstruction implemented.
- Semantic views: Structural (255), Behavioral (1280), Metadata (846) view extraction verified; supports SliceSpec and IndicesSpec; mathematical bounds and disjoint/completeness integrity verified.
- View mapping hash identity: deterministic SHA-256 fingerprint (`276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb`) verified against `configs/views.demo.yaml`; index mutation and tampering detection verified.
- Scientific isolation & fail-closed security: unfreezed scientific mapping in `configs/views.scientific.yaml` safely fails closed (raises RuntimeError) when scientific mode is requested while OQ-01 remains pending freeze.
- Automated tests: 49 targeted tests in `test_be04_domain_schema_views.py`, 53 tests in data test suite (97% active statement coverage), 130 passed across full test suite (2 skipped for unconfigured live DB).
 
## BE-05 Milestone Verification

- Versioned model loading: LightGBM model loading with dimension validation (2,381 features), tree verification (1,000 trees), format validation, and in-memory caching to eliminate redundant 127MB reloads implemented.
- Model identity & artifact integrity: deterministic SHA-256 calculation (`509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2`), mismatch detection, missing/corrupted artifact detection, and structured `ModelMetadata` provenance verified.
- LightGBM inference service: single-sample and batch inference verified; input schema validation enforced via BE-04; output bounds ($P \in [0, 1]$), raw log-odds, and strict determinism verified; zero decision thresholds baked in.
- Local TreeSHAP explainability: exact local TreeSHAP attributions (2,381 features) and constant ensemble base values computed natively via LightGBM C++ TreeSHAP; mathematical additivity ($\sum \text{SHAP} + \text{base} = \text{margin}$) verified to tolerance $10^{-5}$; sequence protocol and batch explanations verified.
- Scientific isolation & fail-closed security: unfreezed scientific config in `configs/model.scientific.yaml` safely fails closed (raises `ModelConfigUnresolvedError`) while OQ-02 is pending; demo adapter disallowed when `allow_demo=False`; zero unauthorized fallback to demo on scientific failure.
- Automated tests: 30 targeted tests in `test_be05_lightgbm_shap_service.py`, 157 passed across full repo suite (5 skipped/deselected for unconfigured live DB).

## BE-06 Milestone Verification

- M1 TADR detector: Canonical temporal/perturbation drift ratio $S_{\text{M1}} = \frac{|\Delta y|}{|\Delta y_{\text{ref}}| + \epsilon}$ implemented with $\epsilon=10^{-12}$, finite float validation, zero-denominator guard, and deterministic `SignalResult` output contract.
- M2 STRIP detector: Tabular STRIP input blending $(1-\alpha)x + \alpha x_b$, Shannon entropy calculation $H(p) = -p\log_2 p - (1-p)\log_2(1-p)$, and mean perturbation entropy $S_{\text{M2}} = \frac{1}{N}\sum H(p_i)$ implemented with $N=16, \alpha=0.2$, seed=42, and deterministic benign pool fallback.
- M3 View Concentration detector: Absolute SHAP sum aggregation per view $c_v = \sum_{j \in V_v} |\phi_j|$, distribution $p_v = \frac{c_v}{\sum c_k}$, normalized entropy $H = -\sum p_v \log_2 p_v$, and concentration score $S_{\text{M3}} = 1 - \frac{H}{\log_2 K}$ implemented.
- M4 Cross-View Disagreement detector: Canonical symmetric cross-view disagreement $S_{\text{M4}} = 0.5 \sum_{i<j} |y_i - y_j| \in [0, 1]$ frozen per ADR-005, alongside 4 ablation strategies (`view_std`, `behavioral_metadata_gap`, `full_vs_behavioral_gap`, `max_pairwise_difference`) configurable via `configs/detector.yaml`.
- M5 Semantic Plausibility detector: Physical PE invariant rule evaluator implemented across 8 canonical rules (`configs/m5_rules.json`); cryptographic SHA-256 verification (`2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d`) enforced fail-closed (`M5RulesIntegrityError`).
- Detector Pipeline: `DetectorPipeline` orchestrates M1..M5 modules against 2,381-vector schema with zero runtime AI/LLM dependencies; returns typed signals and provenance metadata.
- Automated tests: 102 targeted unit and pipeline tests across `test_be06_m1_tadr.py` (19), `test_be06_m2_strip.py` (24), `test_be06_m3_view.py` (16), `test_be06_m4_cross_view.py` (17), `test_be06_m5_semantic.py` (16), and `test_be06_detector_pipeline.py` (10); 262 passed across full repo test suite (2 skipped for unconfigured live DB).

## BE-07 Milestone Verification

- Canonical Fusion Strategy: Convex linear combination $S_{\text{fusion}} = \sum_{i=1}^5 w_i s_i$ with normalized weights $\sum w_i = 1.0$ (`WeightedSumFusion`) implemented and frozen alongside supported strategies (`LogisticRegressionFusion`, `MaxSignalFusion`, `DemoMeanFusion`).
- Signal Input Validation Contract: Strict verification of 5 detector signals (`m1`..`m5`) in $[0.0, 1.0]$, finite numeric floats, case-insensitivity, and `SignalResult` object compatibility with zero silent fallback.
- D0 Calibration: Alert budget operational mode with configurable baseline threshold $\tau_{\text{D0}} = 0.50$ requiring zero trusted reference data.
- D1 Calibration: Empirical quantile threshold calibration targeting False Positive Rate $\le 0.01$ (1%) on trusted benign reference validation set, computing exact empirical FPR and Wilson score 95% confidence intervals ($[0.0054, 0.0183]$ at $N=1000$).
- Calibration Artifact & Cryptographic Integrity: Versioned immutable JSON artifact (`artifacts/calibration/d1_calibration.json`) with SHA-256 payload checksum verification (`e899ad25ef88e267281503012803421816d27b720269f94bd3aca3e64c99fcd3`); tampering and missing artifact fail-closed security enforced.
- Threshold Provenance & Management: Complete `ThresholdProvenance` dataclass tracking threshold ID, mode, value, source, config/artifact hashes, and empirical FPR/Wilson metrics; strict domain validation and boundary testing ($<, ==, >$).
- Decision Policy: 3-state boundary model (`PASS`, `ALERT`, `QUARANTINE`) with strict demo isolation (`DEMO_ONLY` with candidate verdict tracking) and SQL Server check constraint compatibility.
- Golden Decision Cases: 8 canonical reference cases covering clean benign, sub-threshold marginal, exact alert boundary, suspicious alert, exact quarantine boundary, severe trojan, demo mode isolation, and D1 false alarm suppression.
- Zero Jev AI / LLM Dependency: Fusion, calibration, and decision pipeline executes strictly offline with zero external network or AI dependencies.
- Automated tests: 72 targeted tests across `test_be07_calibration.py` (17), `test_be07_threshold_provenance.py` (12), `test_be07_fusion_engine.py` (28), `test_be07_decision_golden_cases.py` (10), and `test_be07_integration.py` (5); 337 passed across full repo test suite.

## BE-08 Milestone Verification

- Canonical Evidence Schema: All 19 fields from `27_EVIDENCE_SCHEMA.md` (`request_id`, `run_id`, `timestamp`, `code_commit`, `build_digest`, `input_id`, `input_mode`, `view_map_hash`, `model_hash`, `model_config_hash`, `detector_config_hash`, `seed`, `malware_score`, `signals`, `fusion_score`, `threshold_id`, `decision`, `latency_ms`, `demo_mode`) implemented with strict domain validation.
- Scientific Acceptance Guard: Enforces hard boundary `validate_for_scientific_acceptance()` which strictly rejects `demo_mode=true` and non-canonical decisions (`ScientificEvidenceRejectedError`).
- Cryptographic Hash Integrity: RFC 8785 / JCS canonical JSON serialization (sorted keys, compact separators `(',', ':')`, UTF-8) with deterministic SHA-256 calculation. Verified invariance to dictionary key ordering and frozen reference golden hash `994e7f813be6702d9d4def0d93edc47ff4dc1fd5249af19e65768d106a59594e`.
- Tamper Resistance: Tampering across any of the 19 fields raises `EvidenceIntegrityError`; in-place mutation prevented by frozen dataclass contract (`EvidenceImmutabilityError` / `FrozenInstanceError`).
- Artifact Contracts: Streaming SHA-256 calculation, metadata preservation, checksum mismatch detection (`ArtifactIntegrityError`), missing file handling (`ArtifactNotFoundError`), and directory traversal prevention (`ArtifactSecurityError`).
- Repositories & SQL Server Persistence: `AnalysisJobRepository`, `AnalysisResultRepository`, `DetectorScoreRepository`, `ArtifactRepository`, `AuditEventRepository` (strictly append-only), and `CanonicalEvidenceRepository` (atomic unit-of-work coordinator) implemented and verified on SQLite and live canonical Microsoft SQL Server.
- Fail-Closed Audit Write Failure: Database commit failures trigger transaction rollback without orphan partial records or false success; unwriteable audit paths raise `AuditWriteFailureError`; scientific detector truth is preserved untouched; zero Jev AI interference during failure handling.
- Automated tests: 46 targeted tests across 7 test suites (`test_be08_canonical_evidence_contract.py` (14), `test_be08_evidence_immutability.py` (3), `test_be08_evidence_hashing_integrity.py` (5), `test_be08_artifact_contracts.py` (8), `test_be08_repositories.py` (8), `test_be08_audit_write_failure.py` (6), `test_be08_end_to_end_integration.py` (2)); 383 passed across full repo test suite.

## BE-09 Milestone Verification

- Core Analysis API: `POST /v1/analyze/vector` validates 2,381-dimensional features, executes detector inference (M1..M5), computes fusion score, persists canonical evidence via `CanonicalEvidenceRepository`, creates alerts for `ALERT` and `QUARANTINE` verdicts, and returns typed `AnalysisResponse`. Phase 2 raw PE upload `/v1/analyze/file` safely gated (501 `XS_FEATURE_DISABLED`).
- Analysis History API: `GET /v1/analysis` provides paginated listing with stable `created_at desc` ordering, supporting filtering by `status`, `decision`, `input_mode`, and `demo_mode`. Detail endpoint `GET /v1/analysis/{analysis_id}` supports lookup by both UUID and `request_id`, returning job metadata, result record, M1..M5 detector scores, and alert references. Missing records return 404 `XS_ANALYSIS_NOT_FOUND`.
- Alerts API: `GET /v1/alerts` lists alerts with pagination and filtering by `severity`, `status`, and `analysis_job_id`. Detail endpoint `GET /v1/alerts/{alert_id}` returns alert metadata. Lifecycle transition endpoint `PATCH /v1/alerts/{alert_id}` strictly enforces allowed state transitions (`open` -> `acknowledged` -> `resolved`/`dismissed`), records resolution timestamps, rejects invalid transitions (400 `XS_INVALID_TRANSITION`), and records append-only audit events.
- Canonical Evidence API: `GET /v1/analysis/{analysis_id}/evidence` provides read-only access to immutable canonical evidence, strictly verifying SHA-256 hash integrity. Tampering triggers 409 `XS_EVIDENCE_INTEGRITY_MISMATCH`; missing records trigger 404 `XS_EVIDENCE_NOT_FOUND`.
- OpenAPI Contract: Generated OpenAPI 3.1.0 schema synchronized with `docs/api/openapi.yaml` (27,531 bytes). All 11 canonical endpoints registered, components schemas validated, security schemes defined (`HTTPBearer`), operation IDs verified unique, and frozen health/readiness contracts preserved.
- Authorization: Server-side authorization verified under `api_auth_mode == "none"` (open dev access) and `api_auth_mode == "bearer"` (enforced token validation). Rejects missing credentials (401 `XS_UNAUTHENTICATED`), invalid tokens (401 `XS_INVALID_CREDENTIALS`), and role violations (403 `XS_FORBIDDEN` for operators accessing evidence or modifying alerts, and evaluators submitting analysis). Blocks client-side header forging.
- Automated tests: 34 targeted tests across 4 test suites (`test_be09_openapi_contract.py` (7), `test_be09_authorization.py` (7), `test_be09_core_api.py` (18), `test_be09_integration.py` (2)); 417 passed across full repo test suite with zero regressions.

## P0 scientific decisions

1. M4 exact canonical formula/normalization: FROZEN (Symmetric Cross-View Disagreement per ADR-005; ablations retained).
2. Fusion/calibration protocol: FROZEN (Canonical `weighted_sum` + D1 empirical quantile calibration at $\text{FPR} \le 1\%$ with Wilson 95% CI; BE-07 scope completed).
3. Scientific LightGBM model identity/config.
4. Authoritative view mapping indices.

## P0 Jev AI integration decisions before enabling in accepted environment

1. Exact LM Studio model ID and model file provenance/license.
2. Context size/resource limits based on actual hardware.
3. Prompt/response retention policy.
4. RBAC roles allowed to invoke AI and read AI outputs.
5. Evaluation set for hallucination/grounding/usefulness.

These do not block detector implementation because Jev AI is optional.
