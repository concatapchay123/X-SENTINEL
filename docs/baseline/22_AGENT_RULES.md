# 22 — AI CODING AGENT RULES

1. Read `README.md`, baseline, requirements, scope, architecture and this file before editing.
2. State the `PLAN-ID`, `TASK-ID`, Requirement IDs and intended files before coding.
3. Do not edit files outside the task's allowed set unless a dependency is explicitly listed.
4. Do not change framework, architecture, input mode, database decision, API contract or detector formula without an approved change request/ADR.
5. Do not add dependencies silently.
6. Do not hard-code thresholds, view indices, secrets, model paths, M2 parameters or M5 bins in business logic.
7. Do not implement a second copy of detector logic in the frontend/API/evaluation layer.
8. Do not read hidden manifest/ground truth from defense code.
9. Do not execute uploaded binaries.
10. Do not call demo-mode outputs scientific evidence.
11. Add/update tests with every behavior change.
12. Run the required task tests before marking REVIEW/DONE.
13. Report changed files, test commands/results, unresolved blockers and evidence paths.
14. Update `17_TRACEABILITY_MATRIX.md` / `18_FEATURE_MATRIX.md` when status changes.
15. API contract changes are contract-first.
16. Schema changes require config/version migration notes.
17. Preserve backwards compatibility unless the plan explicitly authorizes breaking change.
18. Any `[TBD]` encountered is a blocker for that behavior; do not invent a hidden default.
19. `[PROPOSED]` values may be implemented only when explicitly part of the assigned plan and must remain labeled until accepted.
20. A task is DONE only when its Definition of Done is satisfied.

## V2 mandatory database guardrails

21. Read `docs/database/DATABASE_RULES.md` before touching persistence.
22. Never change a DB table/column/index manually; create an Alembic revision.
23. Never edit a shared/applied migration; add a new migration.
24. ORM change without migration is BLOCKED.
25. Migration without rollback/data-compatibility analysis is BLOCKED.
26. API/frontend code may not depend on an unmerged schema change.
27. Never store blind ground truth in application DB.
28. Never store secrets in migrations, seeds or committed env files.
29. Run `make db-check` after every model/migration change.
30. Report migration revision(s) in the task completion summary.
