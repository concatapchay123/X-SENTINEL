# PLAN-09 — Threat Simulation & Manifest Custody

**Objective:** Trigger test data, seeds, poison rates, hidden manifest.

**Scope:** Only the files/modules listed by tasks below.  
**Status:** TODO (baseline created; implementation evidence not assumed).  
**Rollback:** revert the plan commit/config version; never preserve incompatible partial scientific configs.

## Tasks

### TASK-09-01 — Define trigger/poison/seed manifest schema

- **Priority:** P0
- **Difficulty:** M
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Define trigger/poison/seed manifest schema.
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

### TASK-09-02 — Implement isolated manifest writer/custody layout

- **Priority:** P0
- **Difficulty:** M
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Implement isolated manifest writer/custody layout.
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

### TASK-09-03 — Implement E1 attack-run interface without defense leakage

- **Priority:** P0
- **Difficulty:** L
- **Action Chain:** mapped in `16A_ACTION_CHAINS.md`
- **Objective:** Implement E1 attack-run interface without defense leakage.
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
