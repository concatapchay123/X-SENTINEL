# 20 — TEST MATRIX — V3

| Test ID | Requirement | Scenario | Type | Expected |
|---|---|---|---|---|
| TC-01 | FR-001/002 | 2,381 vector schema | Unit | valid accepted; invalid rejected |
| TC-02 | FR-003 | 3-view mapping | Unit | complete/disjoint/versioned |
| TC-03 | FR-020 | raw PE Phase 2 | Integration | static only; malformed safe; equivalent vector |
| TC-04 | FR-004/005 | model/SHAP repeatability | Integration | stable within tolerance |
| TC-05..09 | FR-006..010 | M1–M5 | Unit | frozen formulas/rules |
| TC-10 | FR-012 | D1 calibration | Scientific | threshold + FPR/Wilson evidence |
| TC-11 | NFR-007 | blind isolation | Security | forbidden access absent |
| TC-12..15 | FR-017/018 | E0–E5 metrics | Scientific | actual raw outputs/CI/tests |
| TC-16 | NFR-002 | detector latency | Performance | P50/P95/P99 measured |
| TC-17 | FR-014 | audit integrity | Integration | required fields + hashes |
| TC-18 | FR-016 | frontend core | E2E | exact backend values/error/export |
| TC-19 | FR-019 | Docker/config | Integration | clean startup/migration |
| TC-20 | FR-018 | blind protocol | Security/Scientific | no leakage; independent scoring |
| AI-01 | AI-003 | advisory authority | Unit/API | AI cannot mutate detector result |
| AI-02 | AI-005 | forbidden context | Security | blocked before network |
| AI-03 | AI-001/008 | endpoint policy | Security | local allowed; external blocked by default |
| AI-04 | AI-010 | LM Studio unavailable | Integration | AI error; detector remains available |
| AI-05 | AI-006 | prompt injection string | Security | treated as evidence only |
| AI-06 | AI-009 | audit metadata | DB/Integration | model/prompt/digests/status/latency persisted |
| AI-07 | FR-028 | feedback | API/DB | valid feedback stored; detector unchanged |
| AI-08 | FR-030 | AI status | API | status independent of detector readiness |
| AI-09 | FE-06 | advisory UI | E2E | label/model/run metadata persistent |
| AI-10 | NFR-012 | AI performance | Performance | timeout/concurrency/resource report |
