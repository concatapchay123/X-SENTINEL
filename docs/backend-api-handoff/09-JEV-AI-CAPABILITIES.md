# X-SENTINEL V3 — JEV AI ADVISORY CAPABILITIES

**Document ID:** `XS3-HANDOFF-09`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Local AI Runtime & Advisory Guardrails  

---

## 1. Operational Principles

Jev AI is an offline, local advisory subsystem powered by LM Studio. It provides explainability, threat triage, comparative analysis, and structured reporting.

### 1.1 Non-Negotiable Guardrails
1. **Advisory Only:** Jev AI cannot alter canonical malware scores, detector signals, thresholds, or audit records.
2. **Local Loopback Enforcement:** All HTTP requests are strictly constrained to loopback interfaces (127.0.0.1, localhost).
3. **Structured Typed Decisions:** Responses are parsed into deterministic Pydantic schemas (Choice, Bool, Score).
4. **Prompt Injection Hardening:** Inbound prompts and PE feature names pass through strict sanitization filters.
