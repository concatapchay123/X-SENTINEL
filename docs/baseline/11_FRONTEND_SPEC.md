# 11 — FRONTEND SPEC — V3

## Current runnable technology

Streamlit remains the inherited runnable UI. V3 keeps the frontend behind API contracts so a later React/Next.js replacement is possible without touching detector logic.

## Information architecture

### 1. Analyze
- vector upload/paste
- future raw PE upload only when backend enables Phase 2
- validation state and request metadata
- run analysis action

### 2. Analysis Result
- detector decision banner
- malware score, suspicion score, threshold
- M1–M5 cards
- view contribution visualization
- SHAP top features
- model/config/evidence hashes
- latency and warnings

### 3. Jev AI Explain panel
- separate visual container labeled `AI advisory`
- modes: Explain / Triage / Report Draft
- show model ID, prompt version, run ID, latency and status
- show uncertainty/limitations
- never replace detector decision text

### 4. History
- analyses
- alerts
- evidence/artifact links
- Jev AI runs tied to each analysis

### 5. System Status
- backend health/readiness
- DB migration state
- demo/scientific mode
- Jev AI enabled/status/model ID
- config hashes and blockers

### 6. Evaluation/Admin
- experiment history
- metric tables generated from canonical evidence
- no manual scientific metric editing
- role-gated controls when RBAC is enabled

## UX invariants

1. Canonical detector evidence and Jev AI narrative use different labels/styles.
2. `AI unavailable` must not hide detector result.
3. Every async state has loading/empty/error/retry handling.
4. Demo mode is obvious.
5. Exports use backend evidence, not UI recomputation.
6. Server authorization is authoritative.
7. Jev AI output can be copied/exported only with its run metadata and `AI advisory` label.
