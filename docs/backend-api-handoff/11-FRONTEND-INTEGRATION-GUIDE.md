# X-SENTINEL V3 — FRONTEND INTEGRATION GUIDE

**Document ID:** `XS3-HANDOFF-11`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Client Implementation Guidelines  

---

## 1. Quickstart Guide

Target Base URL: `http://localhost:8000`

### Example Vector Submission:
```bash
curl -X POST http://localhost:8000/v1/analyze/vector \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-analyst-token" \
  -d '{"features": [0.0, 0.1, ..., 0.0], "demo_mode": true}'
```
