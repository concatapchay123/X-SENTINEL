# 26 — RISK REGISTER

| ID | Risk | Severity | Mitigation |
|---|---|---:|---|
| R-01 | M4 spec drift | High | freeze ADR/config; alternatives only in ablation |
| R-02 | Fusion drift/leakage | High | version weights/threshold; calibrate before blind test |
| R-03 | Vector/raw-PE path confusion | High | separate adapters; vector MVP; TC-03 equivalence |
| R-04 | Model config mismatch | High | external config + model hash + release tuple |
| R-05 | Weak attack invalidates detector conclusion | Very High | E1 gate before detector conclusions |
| R-06 | No actual metrics | Very High | artifact-first E0–E5 runner |
| R-07 | D1 non-representative | Med-High | independent/cross-eval benign sets |
| R-08 | M5 hash semantics weak | Medium | lock bins/rules; document limitation |
| R-09 | Ground-truth leakage | Very High | process/path isolation + custody logs |
| R-10 | Threshold tuning after test | Very High | immutable frozen run config |
| R-11 | Demo output mistaken for evidence | High | demo flag in API/UI/audit; acceptance rejects demo artifacts |
| R-12 | Public exposure without auth | High | local bind/default; auth ADR required |
