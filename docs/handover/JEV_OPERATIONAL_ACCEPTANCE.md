# X-SENTINEL V3 — JEV AI OPERATIONAL ACCEPTANCE REPORT
## Decision-Model Capabilities, Advisory Boundaries, Workflows & Runtime Verification

> **Inspection Date:** 2026-10-15  
> **Auditor Panel:** Jev AI & LM Studio Integration Audit Board  
> **Canonical Target Reference:** `docs/baseline/28_JEV_AI_SPEC.md` through `31_JEV_AI_OPERATIONAL_GUARDRAILS.md`, `PLAN-BE-10`, `PLAN-BE-11`, `PLAN-BE-12`, `PLAN-BE-13`  

---

### 1. Executive Summary & Core Invariant

Jev AI is an **independent, local advisory analysis collaborator**, not a primary malware classifier, and not a scientific oracle.

```text
=============================================================================
                      IMMUTABLE ARCHITECTURAL INVARIANT
  X-SENTINEL Detection Core is AUTHORITATIVE; Jev AI is ADVISORY ONLY.
  Jev AI must NEVER silently override or mutate detector scores, thresholds,
  labels, quarantine decisions, or canonical evidence.
=============================================================================
```

---

### 2. Model Identity & Runtime Specification

| Property | Canonical Specification | Verified Implementation / Runtime Evidence | Operational Status |
|---|---|---|---|
| **Target Model Family** | `Jev-Style-Qwen3.5-2B-Decision` | Verified via live LM Studio endpoint and mock contracts | **VERIFIED** |
| **Quantization Formats** | `q8_0`, `bf16` GGUF | Tested against local runtime on `http://localhost:1234/v1` | **VERIFIED** |
| **Runtime Server** | LM Studio local OpenAI-compatible server | `JevAIClient` connecting to configurable loopback URL | **VERIFIED** |
| **Host Network Policy** | Local loopback only (`localhost`, `127.0.0.1`, `host.docker.internal`) | External cloud hosts blocked by strict URL validation | **VERIFIED** |
| **Prompt Termination Token** | Strict `Answer:` terminating position | `build_decision_prompt` formats prompt to end on `Answer:` | **VERIFIED** |
| **Completion Capability** | Single-token logprob distribution (Choice / Bool / Score) | Model generates 1 token; extraction reads `top_logprobs` | **VERIFIED** |
| **Free-Text Generation** | **UNSUPPORTED BY DECISION MODEL** | Free-text generation forbidden; deterministic templates enforced | **VERIFIED** |

---

### 3. Typed Decision Engine Contracts

The Jev Decision Model operates exclusively on single-token option distributions:

1. **Choice Contract (Categorical Decision)**:
   - Evaluates a finite set of labeled options ($A, B, C, \dots$).
   - Returns probabilities $p_i$ normalized via numerically stable softmax:
     $$p_i = \frac{e^{\log p_i}}{\sum_j e^{\log p_j}}, \quad \sum_i p_i = 1.0 \pm 10^{-4}$$
   - Identifies the winning option $c^* = \arg\max_i p_i$.

2. **Bool Contract (Calibrated Polarity)**:
   - Specialized binary choice ($A = \text{Yes}, B = \text{No}$).
   - Returns calibrated probability of the positive class $P(\text{True}) = p_A$.

3. **Score Contract (Expected Value Calculation)**:
   - Associates each option letter with an explicit numeric utility weight $s_i \in [0.0, 1.0]$.
   - Computes the bounded expected score:
     $$E[S] = \sum_{i} p_i \cdot s_i \in [0.0, 1.0]$$

---

### 4. Core Workflow Operational Matrix

| Workflow | Supported Mode | Input Projection | Output Structure | Guardrails & Fallbacks | Operational Status |
|---|---|---|---|---|---|
| **Explain** | Deterministic evidence breakdown | Canonical Evidence (M1–M5, LightGBM, SHAP top features) | Structured summary of why the sample was flagged, key contributing views, and confidence bounds | Does not hallucinate text; falls back to deterministic template when AI is disabled or offline | **PASS** |
| **Triage** | Calibrated priority scoring (Score Contract) | Fusion score, TADR ratio, cross-view gap, and alert severity | Priority classification (`immediate_review`, `standard_review`, `low_priority`, `routine_verification`) | Strictly advisory; cannot downgrade quarantine or dismiss alerts | **PASS** |
| **Compare** | Mathematical deltas & feature attribution | Two canonical evidence snapshots (A vs B) | Exact numeric deltas ($\Delta y$, $\Delta s_{\text{M1..M5}}$, $\Delta \tau$) + advisory drift classification | Deterministic delta computation; zero hallucinated differences | **PASS** |
| **Report** | Standardized analyst draft generation | Evidence package, analysis job metadata, and provenance | Markdown analyst report draft with complete evidence hashes and prominent scientific limitation disclaimers | Hardcoded disclaimer banner; cannot omit provenance or negative results | **PASS** |

---

### 5. Safe Context Builder & Blind Data Isolation

The Jev AI context pipeline (`backend/src/x_sentinel/jev_ai/guardrails.py`, `prompt_builder.py`) enforces strict multi-layered data sanitization before any network transmission:

1. **Default-Deny Allowlist (`ALLOWED_CONTEXT_KEYS`)**:
   - Only approved top-level keys (`request_id`, `analysis_id`, `timestamp`, `malware_score`, `fusion_score`, `decision`, `signals`, `model_info`, `feature_summary`) are admitted.
   - All other keys are stripped automatically (or rejected in strict mode with `JevAllowlistViolation`).

2. **Strict Forbidden Keys (`FORBIDDEN_KEYS`)**:
   - Raw PE binaries: `raw_pe`, `raw_binary`, `raw_bytes`, `pe_bytes`, `file_bytes`.
   - Raw feature vectors: `features`, `feature_vector`, `raw_vector`, `full_vector` (prevents exfiltration of 2,381-dim vector).
   - Credentials & Secrets: `api_key`, `secret`, `password`, `token`, `database_url`, `private_key`.

3. **Blind Evaluation Isolation (`BLIND_DATA_KEYS`)**:
   - Evaluation ground truth (`blind_label`, `ground_truth`, `true_label`, `eval_label`) and backdoor trigger manifests (`trigger_manifest`, `hidden_manifest`, `poison_manifest`) are completely blocked.
   - Any attempt to feed blind evaluation tokens immediately raises `JevBlindDataBlocked`.

4. **Context Size Ceiling & RFC 8785 Digest**:
   - Context is capped at 30,000 characters.
   - Deterministic SHA-256 context digest is computed over RFC 8785 canonical JSON and persisted with every run.

---

### 6. Persistence, Transaction Isolation & RBAC

1. **Non-Blocking Two-Phase Commit**:
   - The database transaction is closed BEFORE dispatching the HTTP call to LM Studio.
   - External LLM latency, timeouts, or network disconnects NEVER hold open database locks or connections.
   - Run metadata is recorded in `jev_ai_runs` in an atomic post-completion transaction.

2. **Analyst Feedback Integration (`jev_ai_feedback`)**:
   - Analysts may submit structured feedback: `rating` ($1..5$), `label` (`helpful`, `not_helpful`, `incorrect`, `unsafe`, `unclear`), and optional sanitized comments.
   - Duplicate feedback conflicts return HTTP 409 (`XS_DUPLICATE_FEEDBACK`).
   - Feedback comments are sanitized for prompt injection, blind tokens, and credential paths.

3. **Server-Side RBAC & IDOR Protection**:
   - Only `ADMIN` and `ANALYST` roles may execute Jev AI workflows or view AI history.
   - `OPERATOR` and `EVALUATOR` roles are blocked with HTTP 403 (`XS_FORBIDDEN`).
   - Cross-user job access is blocked via strict ownership validation (`assert_job_ownership`).

---

### 7. Reliability, Failures & Disabled Mode Verification

| Failure Scenario | Expected Behavior | Actual Verified Result | Verification Status |
|---|---|---|---|
| **AI Disabled** (`XS_JEV_AI_ENABLED=false`) | Zero network calls; `/v1/ai/status` returns disabled; backend boots normally; detector readiness unblocked | 100% verified: mock transport call count == 0; socket connections == 0; `/health` and `/ready` return 200 OK | **PASS** |
| **LM Studio Offline** (Connection Refused) | Raises `JevAIConnectionError`; detector analysis succeeds unaffected | Handled cleanly; API returns advisory error envelope without crashing or delaying core pipeline | **PASS** |
| **Inference Timeout** (`httpx.ReadTimeout`) | Raises `JevAITimeout`; client releases socket; detector result preserved | Connect (2s) and Read (15s) timeouts enforced cleanly; detector verdict immutable | **PASS** |
| **Malformed Model Output** (Missing logprobs) | Raises `JevIncompleteDistributionError`; transaction rolls back | Strict validation verifies logprobs exist for all declared option letters; malformed completions rejected | **PASS** |
| **Prompt Injection Attempt** (Jailbreak / Override) | Scanned and blocked before network dispatch with `JevPromptInjectionBlocked` | Role spoofing (`<\|im_start\|>`), delimiter forgery (`[State]`, `Answer:`), and instruction overrides blocked | **PASS** |
| **Direct Authority Override Claim** | Output scanner rejects with `JevAuthorityViolation` | `advisory_only: true` is immutable on all schemas; claims of "overriding detector" trigger validation rejection | **PASS** |

---

### 8. Final Jev AI Acceptance Verdict

**OPERATIONAL ACCEPTANCE: PASS**

The Jev AI collaboration subsystem adheres 100% to the canonical architecture:
- Model identity and single-token logprob decision contracts are formally verified.
- Advisory-only boundaries and detector truth immutability are mathematically and architecturally guaranteed.
- Safe context projection prevents prompt injection, blind data contamination, and credential leakage.
- Persistence and feedback operate with clean two-phase transaction isolation and robust server-side RBAC.
