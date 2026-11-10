# X-SENTINEL V3 — ERROR CATALOG & RECOVERY

**Document ID:** `XS3-HANDOFF-10`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Error Codes & Client Recovery Protocols  

---

## 1. Error Code Taxonomy

| Error Code | HTTP Status | Root Cause | Client Recovery Action |
| :--- | :--- | :--- | :--- |
| `XS_INPUT_INVALID` | 422 | Vector length not 2,381, NaN, Inf, or boolean values | Verify feature extractor output; ensure exactly 2,381 finite floats. |
| `XS_AUTH_REQUIRED` | 401 | Missing or invalid Bearer token | Authenticate and supply a valid bearer token. |
| `XS_FORBIDDEN` | 403 | Insufficient role permissions or IDOR violation | Request required role (analyst, admin) or access owned records. |
| `XS_NOT_FOUND` | 404 | Target entity does not exist | Check UUID parameter. |
| `XS_INVALID_TRANSITION`| 400 | Attempted alert rewind from terminal state | Terminal states cannot be changed. |
| `XS_AUDIT_WRITE_FAILED`| 500 | Database commit failure or duplicate request_id | Retry with a new request_id. |
| `XS_AI_UNAVAILABLE` | 503 | LM Studio offline, timed out, or bad gateway | Verify LM Studio server is running locally on port 1234. |
| `XS_RAW_PE_DISABLED` | 501 | Raw PE binary ingestion disabled (Phase 2 gate) | Submit pre-extracted 2,381-dim EMBER vector instead. |
| `XS_SYSTEM_OVERLOAD` | 503 | Concurrency budget exhausted | Exponential backoff and retry. |
