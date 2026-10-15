# X-SENTINEL V3 — EVIDENCE INDEX & ARTIFACT INVENTORY
## Traceable Catalog of All System, Test, Scientific, AI & Deployment Evidence

> **Inventory Date:** 2026-10-15  
> **Repository Commit:** Git HEAD (`99797ff`)  
> **Release Bundle Digest:** `sha256:41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb`  
> **Integrity Verification:** 100% SHA-256 Verified  

---

### Evidence Inventory Table

| Evidence ID | Category | Source Requirement | File Path | Producer | Experiment / Test ID | Version / Revision | SHA-256 Digest | Data Classification | Verification Status | Related Gate |
|---|---|---|---|---|---|---|---|---|---|---|
| **EVID-SRC-01** | Source | NFR-001 | `pyproject.toml` | Build System | BE-01 | v0.3.0 | `238b939ba6bb0ec96bb05fa0332822a969fba7599c75908cefb4feae53702f23` | Public / Open | **VERIFIED** | SE-01 |
| **EVID-SRC-02** | Source | FR-022 | `database/migrations/versions/0002_v3_jev_ai_audit.py` | Alembic | BE-02 | `0002_v3_jev_ai_audit` | `9aba657dcf6aef2207cec12d632c25dcbd12a648f2e9de09067bd0d16bffce0a` | Internal / Core | **VERIFIED** | SE-02, BE-02 |
| **EVID-SRC-03** | Source | FR-015 | `docs/api/openapi.yaml` | FastAPI / Routes | BE-09 | v3.1.0 | `611b816f5c88b64e5258e7f5df2ea952d7ee4a1f5926ec39d7894a46c2912440` | Public / Spec | **VERIFIED** | BE-09, BE-16 |
| **EVID-CFG-01** | Config | FR-011 | `configs/detector.yaml` | Detector Team | BE-06, BE-07 | v3.0.0 | `78374ea02719aad0d97277c36afde963c77df858a17f7fe56b8f9bfe4c20057d` | Restricted / Science | **VERIFIED** | SE-03, BE-06 |
| **EVID-CFG-02** | Config | FR-003 | `configs/views.demo.yaml` | Feature Team | BE-04 | v3.0.0 | `d0a4fd5c7fd7b3c5a3735e4bf0b422f1c24b5a8610852ad7f6ae967a470ba55b` | Public / Demo | **VERIFIED** | SE-03, BE-04 |
| **EVID-CFG-03** | Config | FR-010 | `configs/m5_rules.json` | Malware Eng | BE-06 | v3.0.0 | `2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d` | Public / Rulebook | **VERIFIED** | SE-03, BE-06 |
| **EVID-CFG-04** | Config | AI-001 | `configs/jev_ai.yaml` | AI Team | BE-10 | v3.0.0 | `55d315f6adcfce6323c92a5499252037dc29a1b8c2c1922c0792bf55d9922e4c` | Public / Local | **VERIFIED** | SE-03, BE-10 |
| **EVID-MOD-01** | Model | FR-004 | `datasets/ember2018/ember_model_2018.txt` | Endgame / EMBER | BE-05 | 2018.2 | `509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2` | Public / Model | **VERIFIED** | BE-05 |
| **EVID-CAL-01** | Calibration | FR-012 | `artifacts/calibration/d1_calibration.json` | Calibration Tool | BE-07 | D1-v1 | `45bc1eed6edf3c04d4b605de760d0bf96f274ea58f1168602c336f5ffc156fe6` | Restricted / Science | **VERIFIED** | SC-03, BE-07 |
| **EVID-SCI-E0** | Scientific | FR-017 | `artifacts/evaluation/be14_candidate_suite/e0_distributions_seed42/metrics.json` | E0 Runner | E0-Seed42 | v3.0.0 | `5bb11f0612660d5b282928df77c05b8aa3bfb4ca6a9b4001f308e9ce7538c353` | Research Evidence | **VERIFIED** | SC-01, BE-14 |
| **EVID-SCI-E1A** | Scientific | FR-017 | `artifacts/evaluation/be14_candidate_suite/e1_t_concentrated_seed42/metrics.json` | E1 Runner | E1-Concentrated | v3.0.0 | `e5bcad0ef82c7a7f722ea4ca7679ea8848d6fb247895aa3ea68a885cb2ffca56` | Research Evidence | **VERIFIED** | SC-01, BE-14 |
| **EVID-SCI-E1B** | Scientific | FR-017 | `artifacts/evaluation/be14_candidate_suite/e1_t_cross_seed42/metrics.json` | E1 Runner | E1-Cross | v3.0.0 | `60a80e1a1ee40a59a7f34e622b724458df5dbf97ae89d1b6cf099ba82650005a` | Research Evidence | **VERIFIED** | SC-01, BE-14 |
| **EVID-SCI-E1C** | Scientific | FR-017 | `artifacts/evaluation/be14_candidate_suite/e1_t_spread_seed42/metrics.json` | E1 Runner | E1-Spread | v3.0.0 | `cba9e4142750a98bf686940d9d3000632ec21dd1e0beba572d4bfa5638c03788` | Research Evidence | **VERIFIED** | SC-01, BE-14 |
| **EVID-SCI-E2** | Scientific | FR-017 | `artifacts/evaluation/be14_candidate_suite/e2_pooled_seed42/metrics.json` | E2 Runner | E2-Pooled | v3.0.0 | `d60155a5bf9684c3ea80d0d62551cfd7cfc5cfdb8754b5dfd4f0d3e5898d9ba8` | Research Evidence | **VERIFIED** | SC-02, BE-14 |
| **EVID-SCI-E3** | Scientific | FR-017 | `artifacts/evaluation/be14_candidate_suite/e3_paired_catch_miss_seed42/metrics.json` | E3 Runner | E3-CatchMiss | v3.0.0 | `a793a386c9ee18e22851d41334c9c7e0c46b14798e3b7b3664cb3f9e9cf2454a` | Research Evidence | **VERIFIED** | SC-05, BE-14 |
| **EVID-SCI-E4** | Scientific | FR-017 | `artifacts/evaluation/be14_candidate_suite/e4_ablation_seed42/metrics.json` | E4 Runner | E4-Ablation | v3.0.0 | `7ea73d092284e36ce5ae0e3049258296a2ca58cf32d20111166645a27ebaa000` | Research Evidence | **VERIFIED** | SC-05, BE-14 |
| **EVID-SCI-E5** | Scientific | FR-017 | `artifacts/evaluation/be14_candidate_suite/e5_fpr_latency_seed42/metrics.json` | E5 Runner | E5-FPRLatency | v3.0.0 | `871a2575c3ef27c7cfbf989809c91652f1e29e8432314bc3a17df3d2eb1d2449` | Research Evidence | **VERIFIED** | SC-03, SC-04 |
| **EVID-BLD-01** | Blind Custody | FR-018 | `artifacts/evaluation/be14_candidate_suite/blind_e2_pooled_seed42/sealed_predictions.json` | Defense Runner | Blind-E2 | v3.0.0 | `485c524666dc759059e20a4a8448457a0f492da06ddb02aed1de3c32e6a754f9` | Sealed Predictions | **VERIFIED** | Blind Custody |
| **EVID-BLD-02** | Blind Custody | FR-018 | `artifacts/evaluation/be14_candidate_suite/suite_summary.json` | Evaluation Scoring | Suite-Summary | v3.0.0 | `18349479e0a02ef59846b9c9f02c67645d1796c834ea5779093bf77e0e7a2df1` | Research Summary | **VERIFIED** | Blind Custody |
| **EVID-AUD-01** | Audit | FR-014 | `artifacts/audit/events.jsonl` | Audit Logger | BE-08 Suite | v3.0.0 | `df74bb26296ff0a7d5da1ea6a422501a61ae0e5eb46aa27f6735508a6582a893` | Audit Log | **VERIFIED** | SE-04, BE-08 |
| **EVID-PRF-01** | Performance | NFR-002 | `artifacts/performance/p50_p95_p99_report.json` | BE-17 Benchmark | Bench-Perf | v3.0.0 | `87b5a8393e8700201df1c72df89965d1d4022ca933c0be8dc3ee0b2b8e3ea954` | Benchmark Data | **VERIFIED** | SE-05, SC-04 |
| **EVID-PRF-02** | Performance | NFR-012 | `artifacts/performance/ai_timeout_load_report.json` | BE-17 Benchmark | Bench-AI | v3.0.0 | `95a7c292fb2b8da453ffb9087c2b53589bdfae032aebc26fb4c360db9cc97aa9` | Benchmark Data | **VERIFIED** | SE-05, AI-010 |
| **EVID-REL-01** | Release | OPS-004 | `artifacts/release/release_tuple.json` | Release Gate | BE-18 Tuple | v0.3.0 | `a41a45741634b8686d11e5f80b91e9f018e6c466440db73c66fdf3586d0ae513` | Release Artifact | **VERIFIED** | Gate 08 |
| **EVID-REL-02** | Release | OPS-005 | `artifacts/release/release_checklist.json` | Release Gate | BE-18 Checklist | v0.3.0 | `239f1ff4977460c39f1406c54784bf05973b7548f060fe732402a7b8e1f5c6e8` | Release Artifact | **VERIFIED** | Gate 10 |
| **EVID-TST-01** | Software Tests | 14_TEST_STRATEGY | Automated Pytest Suite (993 tests) | Pytest 9.0.3 | Full Regression | v0.3.0 | Log Ref: `task-221.log` (127.99s, 0 failures) | Test Evidence | **VERIFIED** | SE-01..SE-05 |

---

### Integrity Verification Summary

- Total Primary Evidence Records: **25**.
- Verified Intact & Traceable: **25 / 25 (100%)**.
- Damaged, Missing, or Corrupted Evidence Records: **0**.
- Zero Evidence Laundering: Negative results, research viability boundaries, and held-out test performance are cataloged exactly as experimentally measured.
