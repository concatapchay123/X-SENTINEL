# PLAN-07 — Input Schema & View Mapping

**Objective:** 2381 validation and versioned 3-view mapping.

**Scope:** Only the files/modules listed by tasks below.  
**Status:** TODO (baseline created; implementation evidence not assumed).  
**Rollback:** revert the plan commit/config version; never preserve incompatible partial scientific configs.

## Tasks

### TASK-07-01 — Implement 2381 vector validation

- **Priority:** P0
- **Difficulty:** M
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Implement 2381 vector validation.
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

### TASK-07-02 — Implement versioned view mapping loader

- **Priority:** P0
- **Difficulty:** M
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Implement versioned view mapping loader.
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

### TASK-07-03 — Add TC-01/TC-02 fixtures/tests

- **Priority:** P0
- **Difficulty:** M
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Add TC-01/TC-02 fixtures/tests.
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
