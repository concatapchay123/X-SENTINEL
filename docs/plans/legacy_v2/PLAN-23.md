# PLAN-23 — Performance / Fast Path / Observability

**Objective:** timing, P95/P99, circuit breaker evaluation, structured logs.

**Scope:** Only the files/modules listed by tasks below.  
**Status:** TODO (baseline created; implementation evidence not assumed).  
**Rollback:** revert the plan commit/config version; never preserve incompatible partial scientific configs.

## Tasks

### TASK-23-01 — Instrument end-to-end timings

- **Priority:** P1
- **Difficulty:** M
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Instrument end-to-end timings.
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

### TASK-23-02 — Benchmark P50/P95/P99 on declared hardware

- **Priority:** P0
- **Difficulty:** L
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Benchmark P50/P95/P99 on declared hardware.
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

### TASK-23-03 — Evaluate 8ms circuit breaker separately from 10ms SLO

- **Priority:** P1
- **Difficulty:** L
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Evaluate 8ms circuit breaker separately from 10ms SLO.
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

### TASK-23-04 — Verify audit completeness under load/fallback

- **Priority:** P0
- **Difficulty:** L
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Verify audit completeness under load/fallback.
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
