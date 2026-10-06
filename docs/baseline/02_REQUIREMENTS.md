# 02 — REQUIREMENTS — V3

## Functional requirements

| ID | Requirement | Priority |
|---|---|---:|
| FR-001 | Accept exactly 2,381-feature EMBER vectors in canonical Phase-1 mode | P0 |
| FR-002 | Validate count/type/finiteness/request metadata | P0 |
| FR-003 | Split input into versioned Structural / Behavioral/API / Metadata/String views | P0 |
| FR-004 | Load versioned LightGBM and produce deterministic inference | P0 |
| FR-005 | Produce local SHAP values with model/config identity | P0 |
| FR-006 | Compute M1 TADR | P0 |
| FR-007 | Compute M2 Tabular STRIP without manifest leakage | P1 |
| FR-008 | Compute M3 View Contribution | P0 |
| FR-009 | Compute one frozen canonical M4 Cross-View signal | P0 |
| FR-010 | Compute M5 Semantic Plausibility from pre-locked rules | P0 |
| FR-011 | Fuse detector signals through a versioned strategy | P0 |
| FR-012 | Support D1 calibration and D0 operating mode | P0 |
| FR-013 | Produce Pass / Alert / Quarantine canonical decision | P0 |
| FR-014 | Persist structured audit/evidence per request | P0 |
| FR-015 | Provide REST contracts for analysis/result/history/alerts/evidence | P0 |
| FR-016 | Provide operator frontend for input/result/SHAP/views/status/history | P1 |
| FR-017 | Execute threat simulation and E0–E5 experiment workflow | P0 |
| FR-018 | Execute blind evaluation with separated truth custody | P0 |
| FR-019 | Support Dockerized reproducible runtime/CI | P1 |
| FR-020 | Support raw PE/LIEF static parser only after equivalence gate | P2 |
| FR-021 | Persist multi-user operational state in Microsoft SQL Server | P0 |
| FR-022 | Apply schema changes only through Alembic | P0 |
| FR-023 | Detect DB revision drift in readiness | P0 |
| FR-024 | Provide backup/restore and schema-drift workflow | P1 |
| FR-025 | Persist model versions, analyses, detector scores, alerts, artifacts and audit | P0 |
| FR-026 | Support optional Jev AI local explanation/triage/report modes | P1 |
| FR-027 | Persist Jev AI run metadata/output according to retention policy | P1 |
| FR-028 | Capture optional analyst feedback on Jev AI outputs | P2 |
| FR-029 | Keep Jev AI invocation independent from canonical analysis transaction | P0 |
| FR-030 | Expose Jev AI status and advisory endpoints without making them detector-readiness blockers | P1 |

## Jev AI requirements

| ID | Requirement | Priority |
|---|---|---:|
| AI-001 | Run through a configurable LM Studio OpenAI-compatible local endpoint | P0 if enabled |
| AI-002 | Exact model ID must be recorded; architecture/context/quantization/license remain TBD until known | P0 |
| AI-003 | Jev AI is advisory-only and cannot override detector state | P0 |
| AI-004 | Use allowlisted minimized evidence context | P0 |
| AI-005 | Reject blind labels, hidden manifests, raw PE and secrets from context | P0 |
| AI-006 | Treat sample-derived strings as untrusted evidence, never instructions | P0 |
| AI-007 | No autonomous shell/process/tool execution in V3 | P0 |
| AI-008 | No silent fallback to cloud providers | P0 |
| AI-009 | Every run records model ID, prompt version, input/output digest, status and latency | P0 |
| AI-010 | AI failures/timeouts preserve canonical detector result | P0 |

## Non-functional requirements

| ID | Requirement | Acceptance |
|---|---|---|
| NFR-001 | Reproducibility | code/config/model/seed/input identities logged |
| NFR-002 | Detector latency | target P95 <10 ms/file on declared hardware; evidence required |
| NFR-003 | FPR | D1 target ≤1% with Wilson 95% CI; evidence required |
| NFR-004 | Determinism | fixed detector inputs produce stable outputs |
| NFR-005 | Auditability | canonical and AI runs have traceable IDs/hashes |
| NFR-006 | Modularity | detection/platform/AI/frontend boundaries enforced |
| NFR-007 | Isolation | defense/AI cannot read hidden truth |
| NFR-008 | Fail-safe | malformed input/AI outage produces explicit non-destructive failure |
| NFR-009 | Configuration | no scientific/AI runtime settings hard-coded in business logic |
| NFR-010 | Evidence integrity | acceptance artifacts are immutable/versioned/checksummed |
| NFR-011 | Database convergence | same repo revision migrates to same schema |
| NFR-012 | AI resource control | timeout/context/concurrency limits benchmarked on actual hardware |

## Security requirements

| ID | Requirement |
|---|---|
| SEC-001 | Never execute uploaded binaries |
| SEC-002 | Restrict payload/file size and validate formats |
| SEC-003 | Hidden manifest/ground-truth paths inaccessible to defense and Jev AI |
| SEC-004 | No secrets in repository |
| SEC-005 | Network deployment requires approved auth/RBAC |
| SEC-006 | Audit failures are visible |
| SEC-007 | Application DB excludes blind truth |
| SEC-008 | Jev endpoint local-host allowlist by default |
| SEC-009 | No raw PE bytes or secrets in Jev prompts |
| SEC-010 | Sample strings/imports are treated as prompt-injection-capable untrusted data |

## Operational requirements

| ID | Requirement |
|---|---|
| OPS-001 | Health/readiness endpoints |
| OPS-002 | Docker/pinned dependency workflow |
| OPS-003 | dev/test/staging/prod configs |
| OPS-004 | rollback tuple: image/config/model/schema revision |
| OPS-005 | release checksum/evidence manifest |
| OPS-006 | Jev status observable separately from detector readiness |
| OPS-007 | Dataset distribution excludes raw datasets; `datasets/` is user-populated locally |
