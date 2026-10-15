# X-SENTINEL V3 — RELEASE & HANDOVER MANIFEST
## Official Handover Artifacts, Immutable Release Tuple & Cryptographic Signatures

> **Release Version:** 0.3.0  
> **Handover Date:** 2026-10-15  
> **Source Commit Revision:** Git HEAD (`99797ff`)  
> **Primary Checksum Manifest:** `F:\IAM302t\SHA256SUMS.txt`  
> **Release Bundle Cryptographic Digest:**  
> `sha256:41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb`  

---

### 1. Canonical Release Tuple Specification

The release bundle is cryptographically bound to a single immutable SHA-256 digest encompassing source code, container image, database schema, detector configurations, view partitions, and calibration thresholds:

| Tuple Component | Canonical Target / Identity | SHA-256 Digest | Verification Status |
|---|---|---|---|
| **Container Image** | `x-sentinel-backend:test` | `sha256:7ab139a6c5be6aab8f9f1b5ed4c76b4eb7799fa782a533ae22bb4f143d7c99ff` | BUILD VERIFIED |
| **Database Schema** | `0002_v3_jev_ai_audit` | `9aba657dcf6aef2207cec12d632c25dcbd12a648f2e9de09067bd0d16bffce0a` | HEAD VERIFIED |
| **Detector Config** | `configs/detector.yaml` | `78374ea02719aad0d97277c36afde963c77df858a17f7fe56b8f9bfe4c20057d` | FROZEN |
| **View Mapping** | `configs/views.demo.yaml` | `d0a4fd5c7fd7b3c5a3735e4bf0b422f1c24b5a8610852ad7f6ae967a470ba55b` | FROZEN |
| **Calibration Bundle**| `artifacts/calibration/d1_calibration.json` | `45bc1eed6edf3c04d4b605de760d0bf96f274ea58f1168602c336f5ffc156fe6` | FROZEN |
| **Model Metadata** | `models/README.md` | `733d53b5e6b806c1268079ae90a18cf2e790dd9bdbcf95971ed0dd404bb6ed1b` | TRACEABLE |
| **Backend Docker** | `infrastructure/docker/backend.Dockerfile` | `0dceb56a87fc8fa40b8eb502b1e839d3f803b4180379316d107d0f5315a52bef` | BUILD VERIFIED |
| **Frontend Docker** | `infrastructure/docker/frontend.Dockerfile` | `73c7bf8143a1ceae2dcd85b15f10fb292798c9e8effe67c132e8051e46e444e1` | BUILD VERIFIED |
| **Docker Compose** | `docker-compose.yml` | `ca42d0967476de32aebbdd53e97ef44be20654d20c0ef2a2ef4d604f8d2df006` | HARDENED |

---

### 2. Invariant Contracts & Architectural Schemas

- **Feature Vector Dimension**: Exactly 2,381 numerical features validated per input record.
- **Evidence Schema Version**: `v3.0.0` with 19 canonical fields and RFC 8785 JSON hashing.
- **Jev AI Prompt Version**: `jev-v3.0.0` enforcing advisory-only single-token logprob distribution.
- **Database Architecture**: Pure Headless REST API returning standard JSON `{"success": true/false, "data": ..., "error": ...}`; zero Jinja/HTML templates.
- **Security & Authorization**: Server-side RBAC with 5 least-privilege roles, zero committed repository credentials, and blind custody barriers.

---

### 3. Handover Deliverables Directory Layout

```text
F:\IAM302t\
├── docs\
│   ├── handover\
│   │   ├── FINAL_ACCEPTANCE_REPORT.md       <- Master Acceptance & Handover Report
│   │   ├── BE01_BE19_ACCEPTANCE_MATRIX.md   <- Complete 19-plan Audit Matrix
│   │   ├── SE_SC_ACCEPTANCE_MATRIX.md       <- SE-01..05 & SC-01..05 Evaluation
│   │   ├── JEV_OPERATIONAL_ACCEPTANCE.md    <- Jev AI Decision Model Verification
│   │   ├── EVIDENCE_INDEX.md                <- Cryptographic Evidence Catalog
│   │   ├── REPRODUCIBILITY_GUIDE.md         <- Audit & Reproduction Protocol
│   │   ├── OPERATIONS_RUNBOOK.md            <- Systems Administration Runbook
│   │   ├── ROLLBACK_RUNBOOK.md              <- Atomic Rollback Procedures
│   │   ├── KNOWN_LIMITATIONS.md             <- Unwhitewashed Limitations Register
│   │   ├── RISK_REGISTER.md                 <- Systemic Residual Risk Register
│   │   ├── HANDOVER_MANIFEST.md             <- Release & Package Manifest (This File)
│   │   └── SIGNOFF_CHECKLIST.md             <- Formal Acceptance Sign-Off Sheet
│   └── runbooks\
│       ├── DEPLOYMENT_RUNBOOK.md
│       └── ROLLBACK_RUNBOOK.md
├── artifacts\
│   ├── audit\
│   ├── calibration\
│   ├── evaluation\be14_candidate_suite\
│   ├── performance\
│   └── release\
│       ├── release_tuple.json
│       ├── RELEASE_MANIFEST.md
│       └── release_checklist.json
└── SHA256SUMS.txt                           <- Canonical Handover SHA-256 Manifest
```

---

### 4. Verification & Handover Sign-Off Attestation

This release package has been audited by the Independent Acceptance Board:
- **993 Automated Tests Passing** (100% green execution across unit, integration, performance, security, and deployment suites).
- **10 / 10 Release Checklist Gates Passing** (`scripts/release_gate.py`).
- **All E0–E5 Scientific Candidate Artifacts Recomputable** with 0 numerical mismatches (`scripts/verify_scientific_reproducibility.py`).
- **Cryptographic Release Tuple Verified & Frozen** (`scripts/verify_release_tuple.py`).
- **Zero Exposed Secrets & Strict Blind Custody Verified** (`scripts/scan_secrets.py`).
