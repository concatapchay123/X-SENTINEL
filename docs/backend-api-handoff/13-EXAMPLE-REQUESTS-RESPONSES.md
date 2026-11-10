# X-SENTINEL V3 — EXAMPLE REQUESTS & RESPONSES

**Document ID:** `XS3-HANDOFF-13`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Practical HTTP Payloads  

---

## 1. Vector Analysis Request & Response

```http
POST /v1/analyze/vector HTTP/1.1
Host: localhost:8000
Authorization: Bearer dev-analyst-token
Content-Type: application/json

{
  "features": [0.0, ..., 0.0],
  "demo_mode": true
}
```

```json
{
  "request_id": "423ee03c-392b-49a2-9a56-baca377d34ce",
  "malware_score": 0.8421,
  "suspicion_score": 0.7915,
  "decision": "ALERT",
  "signals": {
    "m1": 0.652,
    "m2": 0.120,
    "m3": 0.814,
    "m4": 0.050,
    "m5": 0.000
  },
  "latency_ms": {
    "end_to_end": 42.15
  }
}
```
