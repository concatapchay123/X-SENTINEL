# X-SENTINEL V3 — KNOWN LIMITATIONS REGISTER
## Comprehensive Technical, Scientific, AI & Operational Limitations Catalog

> **Catalog Date:** 2026-10-15  
> **Auditor Panel:** Independent Acceptance & Quality Audit Board  
> **Constitutional Policy:** Strict Anti-Hallucination Contract — Zero Silent TBDs, Zero Whitewashing.  

---

### 1. Scientific & Threat Modeling Limitations

| ID | Title / Limitation | Component | Severity | Scientific & Operational Impact | Workaround / Remediation |
|---|---|---|---|---|---|
| **LIM-SCI-01** | Vector-Only Operational Scope (Phase 1) | Data Ingestion | Medium | The production detector exclusively processes pre-extracted 2,381-dimensional EMBER feature vectors. It does not parse or extract features from raw PE files on disk in production mode. | Raw PE parser adapter developed in BE-19 remains fail-closed until TC-03 equivalence gate is formally approved. Use EMBER offline vectorizer. |
| **LIM-SCI-02** | Unresolved Scientific View Map (`OQ-01`) | Feature Views | High | `configs/views.scientific.yaml` contains `TBD_MUST_FREEZE_BEFORE_SCIENTIFIC_RUN`. Official scientific feature index partitions (V1/V2/V3) are not yet finalized. | System operates using validated `configs/views.demo.yaml`. Strict scientific mode fails closed (`ExperimentBlockedError`). Formal freeze required for scientific release. |
| **LIM-SCI-03** | Unresolved Scientific Model Promotion (`OQ-02`) | Model Service | High | `configs/model.scientific.yaml` contains `TBD_MUST_FREEZE` (`expected_sha256: TBD`). The EMBER2018 model has not been promoted into the scientific freeze configuration. | System operates using `configs/model.ember2018.yaml` (SHA-256 `509de4a8...`). Promote verified checksum into scientific config prior to research sign-off. |
| **LIM-SCI-04** | Missing Poisoned Model Cohort | Threat Evaluation | High | Pre-trained poisoned LightGBM models (`models/*poison*.txt`) for trigger families `T-concentrated`, `T-spread`, `T-cross` (0.5%, 1%, 2% poison rates) are absent from the repository. | Clean-trigger control ASR is verified ($0.0\%$). True backdoor evasion evaluation on poisoned models is BLOCKED until models are trained under an approved protocol. |
| **LIM-SCI-05** | Held-Out Test False Positive Rate Divergence | Calibration & D1 | Critical | The D1 calibration threshold ($\tau = 0.46885$) was computed on a preliminary calibration partition. When evaluated on 25 held-out EMBER2018 test samples, Full Fusion exhibited 100% FPR and Reduced Fusion 80% FPR. | Recalibrate D1 empirical quantile on an independent 1,000-sample benign partition from the target operational distribution once OQ-01/OQ-02 are resolved. |
| **LIM-SCI-06** | Missing Benign Subgroup Metadata | Evaluation | Low | The numerical EMBER2018 feature space does not retain digital certificate signatures, packer flags, or compilation timestamps, preventing empirical subgroup audits (`standard_benign`, `signed_packed_benign`, `rare_benign`). | Marked `BLOCKED_MISSING_SUBGROUP_LABELS` in E5 report. Future work requires raw PE corpus with Rich Header and authenticode signature metadata. |
| **LIM-SCI-07** | STRIP Perturbation Stochasticity | M2 STRIP | Low | M2 Tabular STRIP blends inputs with randomly sampled benign baseline vectors. Variations in random seed or pool composition produce minor variance in entropy scores. | Locked to pseudo-random seed (`seed=42`) and 32-sample frozen benign pool (`be14_m2_strip_pool_v1`) to guarantee reproducibility. |

---

### 2. Jev AI Collaborator Limitations

| ID | Title / Limitation | Component | Severity | Scientific & Operational Impact | Workaround / Remediation |
|---|---|---|---|---|---|
| **LIM-AI-01** | Decision-Only Model Architecture | Jev AI Core | Medium | The local runtime model (`Jev-Style-Qwen3.5-2B-Decision`) is fine-tuned strictly for single-token logprob classification (Choice, Bool, Score). It does NOT generate coherent free-text explanations. | Workflows (Explain, Report) utilize structured deterministic Markdown templates populated from canonical evidence, bypassing unstructured LLM hallucinations. |
| **LIM-AI-02** | Advisory-Only Authority Boundary | AI Orchestrator | Low (By Design) | Jev AI cannot override, mutate, or dismiss any canonical detector verdict, malware score, or quarantine state. | Non-negotiable architectural invariant. All schemas enforce immutable `advisory_only: true`. |
| **LIM-AI-03** | Context Window & Token Budget Limit | Context Builder | Low | Context input is capped at 30,000 characters to prevent LM Studio context overflow and excessive local CPU inference latency. | Safe Context Builder automatically redacts non-allowlisted keys, trims verbose feature lists, and calculates an RFC 8785 context digest. |
| **LIM-AI-04** | Local-Only Loopback Policy | Runtime Client | Low (By Design) | In compliance with cybersecurity requirements, Jev AI cannot access cloud LLM providers (OpenAI, Anthropic, Gemini). Network egress is blocked by design. | Operators must host an OpenAI-compatible local server (LM Studio or vLLM) on the local host or Docker bridge. |
| **LIM-AI-05** | English Task-Family Bias | Decision Prompts | Low | Prompts and option definitions are formulated in technical cybersecurity English. Non-English queries may experience degraded option logprob calibration. | Operator interfaces should query Jev AI using standardized English technical terminology. |

---

### 3. Performance & Resource Limitations

| ID | Title / Limitation | Component | Severity | Scientific & Operational Impact | Workaround / Remediation |
|---|---|---|---|---|---|
| **LIM-PRF-01** | End-to-End Latency on TreeSHAP | Performance | Medium | Full pipeline execution with TreeSHAP over 1,000 LightGBM trees and 16 STRIP perturbations requires ~1.20s P50 and ~1.26s P95 per file on standard CPU hardware. | For high-throughput scenarios, use Fast-Path inference (detector-only without TreeSHAP: ~35-41ms P95) and offload TreeSHAP asynchronously. |
| **LIM-PRF-02** | Historical $<10\text{ ms}$ P95 Target Unmet | Performance | Medium | The historical proposal target of P95 $< 10\text{ ms/file}$ was based on unverified C++ GPU expectations. On Python CPU runtime, full end-to-end execution exceeds this threshold. | Documented honestly as a historical artifact target; current operational SLA is $< 100\text{ ms}$ for detector-only and $< 2.0\text{ s}$ for end-to-end. |
| **LIM-PRF-03** | Concurrency Bounded by CPU Cores | Concurrency | Medium | High concurrent analysis loads (>25 concurrent requests) without worker process scaling cause queue latency growth due to GIL and OpenMP thread contention in LightGBM. | Configured concurrency semaphores (max 50 requests) and recommended multi-worker Uvicorn deployment behind reverse proxy. |

---

### 4. Security & Deployment Limitations

| ID | Title / Limitation | Component | Severity | Scientific & Operational Impact | Workaround / Remediation |
|---|---|---|---|---|---|
| **LIM-SEC-01** | Raw PE Production Gating | Security / PE Parser | Medium | `POST /v1/analyze/file` returns HTTP 501 (`XS_FEATURE_DISABLED`). Static PE extraction is implemented and hardened against malformed files, but gated due to LIEF 1.0 vs 0.9 library drift. | Operators must ingest pre-vectorized EMBER vectors until Phase 2 equivalence sign-off is granted by the Change Control Board. |
| **LIM-SEC-02** | Microsoft SQL Server Dependency | Persistence | Medium | Multi-user role-based security, transaction isolation, and audit append-only immutability require an active Microsoft SQL Server instance. SQLite is supported only for local testing. | Staging and Production deployments must connect to a verified Microsoft SQL Server 2022 instance with `0002_v3_jev_ai_audit` applied. |
| **LIM-SEC-03** | Host OS Sandbox Boundary | Security | Low | The application does not execute untrusted binaries, but relies on container isolation (non-root UID 10001) for defense-in-depth against underlying OS vulnerabilities. | Container deployments must adhere to non-root execution guidelines and mount volumes with read-only permissions where applicable. |

---

### 5. Summary Scope Classification

- **IMPLEMENTED & VERIFIED**: EMBER 2,381 schema, LightGBM/TreeSHAP service, M1–M5 detector core, Fusion engine, D1 calibration engine, Canonical Evidence contract, Core REST APIs, Jev AI decision engine & guardrails, Two-phase persistence, Docker build, and Migration gate.
- **EXPERIMENTAL / CANDIDATE ONLY**: E0–E5 threat simulation evaluation suite, Candidate D1 calibration threshold ($\tau = 0.46885$).
- **DISABLED BY DESIGN (FAIL-CLOSED)**: Raw PE file ingestion API (`/v1/analyze/file`), Cloud LLM fallback egress.
- **BLOCKED PENDING INPUTS**: Strict scientific freeze sign-off (`OQ-01`, `OQ-02`, pre-trained poisoned LightGBM models).
