# X-SENTINEL V3 — FINAL DEFECT REGISTER

**Status:** **16 / 16 DEFECTS RESOLVED (100% CLOSED)**

| Defect ID | Description | Component | Severity | Status | Verification Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| DEF-001 | Missing 24 Legacy Plans | Repo Hygiene | P0 | RESOLVED | `scripts/baseline_audit.py` passed |
| DEF-002 | Semantic View Permissiveness | Feature Schema| P1 | RESOLVED | `test_be04_domain_schema_views.py` passed |
| DEF-003 | Unmasked Password in Doc | Secret Scanner| P0 | RESOLVED | `scripts/scan_secrets.py` 0 findings |
| DEF-004 | Hostile URL Binding in Jev | AI Client | P1 | RESOLVED | `test_be10_jev_ai_runtime_client.py` passed |
| DEF-005 | M1 Zero Std Division | Detection M1 | P2 | RESOLVED | `test_be06_m1_tadr.py` passed |
| DEF-006 | McNemar Zero Discordance | Statistics | P2 | RESOLVED | `test_be14_threat_simulation.py` passed |
| DEF-007 | SQLite Scratch Lock | Test Fixtures | P1 | RESOLVED | `test_be16_database_resilience.py` passed |
| DEF-008 | Alert State Machine Rewind | Alert Lifecycle| P2 | RESOLVED | `test_be09_core_api.py` passed |
| DEF-009 | Concurrency Permit Leak | Monitoring | P1 | RESOLVED | `test_be17_concurrency_budgets.py` passed |
| DEF-010 | Mutable Artifacts in Checksum | Packaging | P1 | RESOLVED | `scripts/verify_sha256sums.py` passed |
| DEF-011 | Handover Doc Naming Drift | Docs | P3 | RESOLVED | Direct inspection confirmed |
| DEF-012 | Release Checklist Mutation | Release Gate | P1 | RESOLVED | `scripts/release_gate.py` passed |
| DEF-013 | Concurrent Session Collision | DB Repository | P1 | RESOLVED | `test_be16_database_resilience.py` passed (6/6) |
| DEF-014 | M1 TADR Top-k Config Missing | Detection M1 | P2 | RESOLVED | `test_be06_m1_tadr.py` passed |
| DEF-015 | M5 Polarity Inversion | Detection M5 | P2 | RESOLVED | `test_be06_m5_semantic.py` passed |
| DEF-016 | Frontend Lock Empty Dir Bypass| Governance | P1 | RESOLVED | `test_verify_frontend_lock.py` passed (13/13) |
