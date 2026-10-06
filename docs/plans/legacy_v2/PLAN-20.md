# PLAN-20 — Metrics & Statistical Validation

**Objective:** AUROC/FPR/Recall/ASR/Wilson/paired tests/latency stats.

**Scope:** Only the files/modules listed by tasks below.  
**Status:** TODO (baseline created; implementation evidence not assumed).  
**Rollback:** revert the plan commit/config version; never preserve incompatible partial scientific configs.

## Tasks

### TASK-20-01 — Implement ASR/AUROC/FPR/Recall metrics

- **Priority:** P0
- **Difficulty:** L
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Implement ASR/AUROC/FPR/Recall metrics.
- **Input:** approved upstream plan outputs/configs.
- **Files to create/modify:** only the module owned by this plan plus tests/docs/traceability.
- **Files not allowed to modify:** unrelated detector formulas, API contract, hidden manifest, acceptance thresholds unless this task explicitly owns them.
- **Dependencies:** previous required plan(s) in execution order.
- **Database impact:** N/A for MVP unless plan explicitly states otherwise.
- **API impact:** update contract first if transport shape changes.
- **Frontend impact:** frontend may consume only documented API/domain outputs.
- **Security:** preserve no-execution and ground-truth-isolation rules.
- **Tests:** unit/integration/contract tests appropriate to the behavior; source TC mapping when applicable.
- **Expected result:** deterministic, versioned behavior with evidence.
- **Acceptance criteria:** task behavior is testable and all required tests pass.
- **Definition of Done:** code + tests + docs/traceability + evidence; no unresolved Critical issue introduced.
- **Rollback:** revert code/config artifact as one compatible unit.

### TASK-20-02 — Implement Wilson CI + paired DeLong/bootstrap protocol

- **Priority:** P0
- **Difficulty:** XL
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Implement Wilson CI + paired DeLong/bootstrap protocol.
- **Input:** approved upstream plan outputs/configs.
- **Files to create/modify:** only the module owned by this plan plus tests/docs/traceability.
- **Files not allowed to modify:** unrelated detector formulas, API contract, hidden manifest, acceptance thresholds unless this task explicitly owns them.
- **Dependencies:** previous required plan(s) in execution order.
- **Database impact:** N/A for MVP unless plan explicitly states otherwise.
- **API impact:** update contract first if transport shape changes.
- **Frontend impact:** frontend may consume only documented API/domain outputs.
- **Security:** preserve no-execution and ground-truth-isolation rules.
- **Tests:** unit/integration/contract tests appropriate to the behavior; source TC mapping when applicable.
- **Expected result:** deterministic, versioned behavior with evidence.
- **Acceptance criteria:** task behavior is testable and all required tests pass.
- **Definition of Done:** code + tests + docs/traceability + evidence; no unresolved Critical issue introduced.
- **Rollback:** revert code/config artifact as one compatible unit.

### TASK-20-03 — Implement latency summaries P50/P95/P99

- **Priority:** P0
- **Difficulty:** M
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Implement latency summaries P50/P95/P99.
- **Input:** approved upstream plan outputs/configs.
- **Files to create/modify:** only the module owned by this plan plus tests/docs/traceability.
- **Files not allowed to modify:** unrelated detector formulas, API contract, hidden manifest, acceptance thresholds unless this task explicitly owns them.
- **Dependencies:** previous required plan(s) in execution order.
- **Database impact:** N/A for MVP unless plan explicitly states otherwise.
- **API impact:** update contract first if transport shape changes.
- **Frontend impact:** frontend may consume only documented API/domain outputs.
- **Security:** preserve no-execution and ground-truth-isolation rules.
- **Tests:** unit/integration/contract tests appropriate to the behavior; source TC mapping when applicable.
- **Expected result:** deterministic, versioned behavior with evidence.
- **Acceptance criteria:** task behavior is testable and all required tests pass.
- **Definition of Done:** code + tests + docs/traceability + evidence; no unresolved Critical issue introduced.
- **Rollback:** revert code/config artifact as one compatible unit.

### TASK-20-04 — Generate machine-readable metric tables

- **Priority:** P0
- **Difficulty:** M
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Generate machine-readable metric tables.
- **Input:** approved upstream plan outputs/configs.
- **Files to create/modify:** only the module owned by this plan plus tests/docs/traceability.
- **Files not allowed to modify:** unrelated detector formulas, API contract, hidden manifest, acceptance thresholds unless this task explicitly owns them.
- **Dependencies:** previous required plan(s) in execution order.
- **Database impact:** N/A for MVP unless plan explicitly states otherwise.
- **API impact:** update contract first if transport shape changes.
- **Frontend impact:** frontend may consume only documented API/domain outputs.
- **Security:** preserve no-execution and ground-truth-isolation rules.
- **Tests:** unit/integration/contract tests appropriate to the behavior; source TC mapping when applicable.
- **Expected result:** deterministic, versioned behavior with evidence.
- **Acceptance criteria:** task behavior is testable and all required tests pass.
- **Definition of Done:** code + tests + docs/traceability + evidence; no unresolved Critical issue introduced.
- **Rollback:** revert code/config artifact as one compatible unit.
