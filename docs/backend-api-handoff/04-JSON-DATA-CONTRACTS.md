# X-SENTINEL V3 — JSON DATA CONTRACTS

**Document ID:** `XS3-HANDOFF-04`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Schema Specifications & Enums  

---

## 1. Global Response Envelope

All API endpoints serialize business responses conforming to the standard JSON structure:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "timestamp": "2026-10-16T13:30:00Z",
    "request_id": "7a958696-5345-434c-a842-dc9611570c1c"
  }
}
```

### 1.1 Error Envelope (4xx / 5xx)
```json
{
  "detail": {
    "code": "XS_INPUT_INVALID",
    "message": "Feature vector must contain exactly 2,381 elements; received 2380."
  }
}
```

---

## 2. Core Request & Response Models

### 2.1 `VectorAnalysisRequest`
| Field | Type | Required | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `features` | `list[float]` | Yes | `len == 2381`, all finite | Normalized EMBER feature vector |
| `input_id` | `string` | No | SHA-256 regex | Digest of binary |
| `demo_mode` | `boolean` | No | Default `false` | Force demo mode evaluation |

### 2.2 `AnalysisResponse`
| Field | Type | Required | Range / Enum | Description |
| :--- | :--- | :--- | :--- | :--- |
| `request_id` | `string` | Yes | UUID format | Unique trace ID |
| `malware_score` | `float` | Yes | 0.0 to 1.0 | LightGBM base prediction |
| `suspicion_score`| `float` | Yes | 0.0 to 1.0 | Fusion engine suspicion |
| `decision` | `string` | Yes | `PASS`, `ALERT`, `QUARANTINE`, `DEMO_ONLY` | Final operational verdict |
| `signals` | `object` | Yes | Keys: `m1`, `m2`, `m3`, `m4`, `m5` | Detector sub-scores |
| `latency_ms` | `object` | Yes | Key: `end_to_end` | Microsecond-accurate latency |

### 2.3 `AlertStatusUpdateRequest`
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `status` | `string` | Yes | One of: `open`, `acknowledged`, `resolved`, `dismissed` |
| `resolution_reason`| `string` | Conditional| Required if status is `resolved` or `dismissed` |

### 2.4 `JevExplainRequest`
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `analysis_id` | `string` | Yes | UUID of target analysis job |
| `workflow` | `string` | Yes | One of: `explain`, `triage`, `compare`, `report` |
| `custom_prompt` | `string` | No | Optional analyst query |
