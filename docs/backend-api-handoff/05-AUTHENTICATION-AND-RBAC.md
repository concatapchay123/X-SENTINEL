# X-SENTINEL V3 — AUTHENTICATION & RBAC SPECIFICATION

**Document ID:** `XS3-HANDOFF-05`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Security Architecture & Authorization  

---

## 1. Authentication Protocol

The platform implements RFC 6750 Bearer Token authentication via the standard HTTP header:
```http
Authorization: Bearer <token>
```

### 1.1 Development vs Production Fail-Closed Protocol
- **Development Mode (`XS_DEV_MODE=true`):** Allows simulated bearer tokens (`dev-analyst-token`, `dev-admin-token`, `dev-operator-token`) for hermetic local testing.
- **Production Mode (`XS_DEV_MODE=false`):** **Strictly fails closed**. Any synthetic dev token, missing token, expired token, or signature mismatch returns HTTP 401 Unauthorized (`XS_AUTH_REQUIRED`).

---

## 2. Role-Based Access Control (RBAC) Hierarchy

The platform defines four mutually exclusive roles:

| Role Name | Authority Scope | Allowed Operations |
| :--- | :--- | :--- |
| `operator` | L1 SOC Operations | Submit vectors for detection, view basic system health and AI status. |
| `analyst` | L2 Threat Investigation | All Operator permissions + query analysis history, view evidence, manage alert lifecycles, run Jev AI advisory workflows, and submit feedback. |
| `admin` | System Administration | All Analyst permissions + system configuration status, metrics scraping, and raw PE administrative gates. |
| `evaluator` | Independent Testing | Isolated offline evaluation and benchmarking endpoints only. Strictly barred from live operational endpoints. |

---

## 3. Object-Level Authorization (Anti-IDOR / Anti-BOLA)

To eliminate Insecure Direct Object References:
1. Every `AnalysisJob` and `JevAIRun` records `user_id` ownership.
2. An Analyst can only view or export canonical evidence for jobs they own, unless their role is `admin`.
3. An Analyst cannot submit feedback on a `JevAIRun` initiated by another analyst.
