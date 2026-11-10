# X-SENTINEL V3 — FRONTEND-READY HANDOFF

**Document ID:** `XS3-HANDOFF-17`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Frontend Engineering Readiness Guide  

---

## 1. Screen-to-API Mapping for Future UI

1. System Dashboard -> `GET /health`, `GET /ready`, `GET /v1/config/status`
2. Vector Analysis Workspace -> `POST /v1/analyze/vector`
3. Analysis History Explorer -> `GET /v1/analysis`, `GET /v1/analysis/{<built-in function id>}`
4. Evidence & Forensics View -> `GET /v1/analysis/{<built-in function id>}/evidence`
5. Security Alerts Workbench -> `GET /v1/alerts`, `PATCH /v1/alerts/{<built-in function id>}`
6. Jev AI Copilot Drawer -> `GET /v1/ai/status`, `POST /v1/ai/explain`, `POST /v1/ai/runs/{<built-in function id>}/feedback`
