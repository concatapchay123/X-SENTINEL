# X-SENTINEL V3 — BACKEND EXECUTIVE SUMMARY

**Document ID:** `XS3-HANDOFF-00`  
**Version:** 3.0.0 (Pure Headless JSON REST Standard Edition)  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Technical Architecture & Frontend Integration Specification  
**Authority:** Principal Software Architect & Multi-Agent Engineering Lead  

---

## 1. System Mission & Architecture Overview

**X-SENTINEL V3** is a high-assurance, defense-in-depth malware detection and decision-support platform designed to analyze Windows Portable Executable (PE) feature vectors with rigorous mathematical guarantees, sub-millisecond local explainability, and cryptographically verifiable canonical evidence.

The platform is strictly structured into three decoupled operational tiers:
1. **Canonical Detection Domain:** The deterministic, mathematically bounded detection core comprising:
   - EMBER 2,381-dimensional normalized feature extraction and validation.
   - Three-view feature decomposition (Byte/Histogram, Structural/PE, Behavioral/Imports).
   - LightGBM gradient boosted tree classifier calibrated for low false-positive operational regimes.
   - TreeSHAP local feature attribution with Top-k dominance ranking (M1 TADR).
   - Specialized detectors: M1 (Top-k TADR), M2 (Tabular STRIP Shannon entropy), M3 (View Concentration), M4 (Symmetric Cross-View Disagreement), and M5 (PE Semantic Plausibility invariants).
   - Weighted Fusion Engine mapping five detector signals into a composite suspicion score with dual-threshold calibration (D0 Alert, D1 Quarantine).
2. **Jev AI Advisory Domain:** A strictly read-only, advisory local LLM subsystem (interfacing via LM Studio):
   - Consumes structured, context-projected telemetry from the detection engine.
   - Executes typed decision workflows (`explain`, `triage`, `compare`, `report`) yielding machine-enforced Pydantic contracts (Choice, Bool, Score).
   - Strictly forbidden from modifying detector scores, thresholds, or canonical audit trails.
3. **Platform & Persistence Domain:** An enterprise-grade, headless REST API backend built on FastAPI, SQLAlchemy, and SQL Server / SQLite:
   - 100% standardized JSON envelope (`success`, `data`, `error`).
   - Pure headless design (zero Jinja templates, zero server-side static assets).
   - Cryptographically enforced audit log immutability and HMAC/SHA-256 evidence chains.
   - Role-Based Access Control (RBAC) and strict owner-based Object-Level Authorization (zero IDOR/BOLA).

---

## 2. Readiness Classification & Operational State

In strict adherence to the **Anti-Hallucination Contract**, the platform's readiness states are formally distinguished:

| Functional Capability | Readiness Level | Operational Status | Public API Route |
| :--- | :--- | :--- | :--- |
| **Vector Ingestion & Validation** | `PRODUCTION_READY` | Active (2,381 dims, strict finite float) | `POST /v1/analyze/vector` |
| **M1–M5 Detectors & Fusion** | `PRODUCTION_READY` | Active (Golden cases verified, deterministic) | Embedded in Analysis |
| **Canonical Evidence Chain** | `PRODUCTION_READY` | Active (HMAC/SHA-256 verified) | `GET /v1/analysis/{<built-in function id>}/evidence` |
| **Analysis History & Details** | `PRODUCTION_READY` | Active (Pagination, RBAC, tenant-safe) | `GET /v1/analysis`, `GET /v1/analysis/{<built-in function id>}` |
| **Security Alert Lifecycle** | `PRODUCTION_READY` | Active (State machine guarded, reasons saved) | `GET /v1/alerts`, `PATCH /v1/alerts/{<built-in function id>}` |
| **Jev AI Advisory Workflows** | `INTEGRATION_READY` | Active (LM Studio local loopback required) | `POST /v1/ai/explain`, `GET /v1/ai/runs` |
| **System Health & Telemetry** | `PRODUCTION_READY` | Active (Real psutil OS metrics, non-blocking) | `GET /health`, `GET /ready`, `GET /v1/config/status` |
| **D1 Held-Out Calibration** | `EXPERIMENTAL_GATED`| Demo/Constrained Mode (Held-out divergence) | Guarded via `demo_mode: true` |
| **Raw PE Binary Extraction** | `FAIL_CLOSED_GATED` | HTTP 501 Not Implemented (Gate prerequisite) | `POST /v1/analyze/file` |

---

## 3. Frontend Lock & Integration Mandate

All legacy frontend files and blueprints are sealed under **Cryptographic Lock** (`FRONTEND_STATUS = LOCKED_BY_USER`, 31 files hashed in `docs/governance/FRONTEND_LOCK_MANIFEST.json`).

Future frontend user interfaces must integrate exclusively through the standardized OpenAPI 3.1 REST API described in this catalog. No direct database queries, private Python imports, or heuristic contract assumptions are permitted.
