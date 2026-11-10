# X-SENTINEL V3 — DANH MỤC VÀ ĐẶC TẢ HỢP ĐỒNG API TOÀN DIỆN
## 03-API-CATALOG.md — Complete API Endpoint Catalog & Request/Response Contracts

> **Mục tiêu:** Cung cấp tài liệu tra cứu hợp đồng API hoàn chỉnh, chính xác 100% so với mã nguồn thực tế (`x_sentinel/api/routes.py`, `schemas.py`, `main.py`, `docs/api/openapi.yaml`).  
> **Cam kết:** Không cắt xén code, không viết tắt, không sử dụng placeholder, schema JSON đầy đủ từng trường.

---

## 1. BẢNG TỔNG QUAN DANH MỤC 21 HTTP OPERATIONS (19 PATH TEMPLATES)

> **Cơ cấu phân loại 21 HTTP Operations (19 Unique Path Templates):**
> - **18 operations nằm trong OpenAPI 3.1 specification:** Gồm 16 operations nghiệp vụ hoạt động trực tiếp + 2 operations được cấu hình khóa an toàn kiểu đóng (Fail-Closed 501: `POST /v1/analyze/file` và `POST /v1/ai/docs/ask`).
> - **3 operations hạ tầng/vận hành nội bộ (`include_in_schema=False`):** `GET /v1/system/telemetry` (API-19), `GET /v1/system/metrics` (API-20), `GET /metrics` (API-21).
> - **Tổng cộng:** 18 (OpenAPI) + 3 (Nội bộ/Ẩn) = **21 HTTP Operations** trên **19 Unique Paths** (do `/v1/alerts/{alert_id}` có GET & PATCH; `/v1/ai/runs/{run_id}/feedback` có POST & GET).

| API ID | Phương thức | Đường dẫn Route | Module sở hữu | Xác thực & Quyền | Mã HTTP chính | Mục đích nghiệp vụ |
|---|:---:|---|---|---|:---:|---|
| **API-01** | `GET` | `/health` | System | Public (None) | `200` | Kiểm tra liveness cơ bản |
| **API-02** | `GET` | `/ready` | System | Public (None) | `200`, `503` | Kiểm tra readiness và danh sách blocker |
| **API-03** | `GET` | `/v1/config/status` | System | Public (None) | `200` | Xem trạng thái cấu hình không nhạy cảm |
| **API-04** | `GET` | `/v1/ai/status` | Jev AI | Public (None) | `200` | Thăm dò kết nối LM Studio cục bộ |
| **API-05** | `POST` | `/v1/analyze/vector` | Analysis | Operator, Analyst, Admin | `200`, `422`, `429`, `409` | Phân tích vector EMBER 2.381 chiều |
| **API-06** | `POST` | `/v1/analyze/file` | Analysis | Public / Tất cả | `501` (Gated) | Khóa an toàn tải tệp PE nhị phân thô (Phase 2) |
| **API-07** | `GET` | `/v1/analysis` | History | Operator, Analyst, Evaluator, Admin | `200`, `401` | Lấy danh sách lịch sử phân tích |
| **API-08** | `GET` | `/v1/analysis/{analysis_id}` | History | Operator, Analyst, Evaluator, Admin | `200`, `403`, `404` | Lấy chi tiết bản ghi phân tích & điểm M1-M5 |
| **API-09** | `GET` | `/v1/analysis/{analysis_id}/evidence` | Evidence | Analyst, Evaluator, Admin | `200`, `403`, `404`, `409` | Lấy bằng chứng pháp chứng & xác minh băm |
| **API-10** | `GET` | `/v1/alerts` | Alerts | Operator, Analyst, Admin | `200`, `401` | Lấy danh sách cảnh báo an ninh SOC |
| **API-11** | `GET` | `/v1/alerts/{alert_id}` | Alerts | Operator, Analyst, Admin | `200`, `404` | Xem chi tiết cảnh báo đơn lẻ |
| **API-12** | `PATCH` | `/v1/alerts/{alert_id}` | Alerts | Analyst, Admin | `200`, `400`, `403`, `404` | Cập nhật trạng thái vòng đời cảnh báo (`{"status": str}`) |
| **API-13** | `POST` | `/v1/ai/explain` | Jev AI | Analyst, Admin | `200`, `403`, `404`, `422`, `429`, `503`, `504` | Thực thi luồng suy luận cố vấn AI |
| **API-14** | `GET` | `/v1/ai/runs` | Jev AI | Analyst, Admin | `200`, `401` | Lấy danh sách các lượt chạy của Jev AI |
| **API-15** | `GET` | `/v1/ai/runs/{run_id}` | Jev AI | Analyst, Admin | `200`, `403`, `404` | Lấy chi tiết kết quả lượt chạy Jev AI |
| **API-16** | `POST` | `/v1/ai/runs/{run_id}/feedback` | Jev AI | Analyst, Admin | `201`, `400`, `409` | Gửi phản hồi đánh giá chất lượng AI |
| **API-17** | `GET` | `/v1/ai/runs/{run_id}/feedback` | Jev AI | Analyst, Admin | `200`, `403`, `404` | Lấy danh sách đánh giá của lượt chạy AI |
| **API-18** | `POST` | `/v1/ai/docs/ask` | Jev AI | Analyst, Admin | `501` (Gated) | Khóa an toàn tính năng hỏi đáp tài liệu (Phase 2) |
| **API-19** | `GET` | `/v1/system/telemetry` | System | Operator, Admin | `200`, `403`, `404` | Đo lường telemetry CPU, RAM, OS thực tế qua `psutil` (`include_in_schema=False`) |
| **API-20** | `GET` | `/v1/system/metrics` | System | Operator, Admin | `200`, `403`, `404` | Thu thập Prometheus exposition metrics có xác thực (`include_in_schema=False`) |
| **API-21** | `GET` | `/metrics` | System | Public (None) | `200`, `404` | Prometheus scrape endpoint cho monitoring stack (`include_in_schema=False`) |

---

## 2. QUY ƯỚC CHUNG VỀ REQUEST VÀ RESPONSE

### 2.1. Cấu hình Cơ sở (Base URL & Headers)
- **Base URL:** `http://localhost:8000` (môi trường cục bộ) hoặc cấu hình qua biến môi trường `XS_API_BASE_URL`.
- **Request Headers chuẩn:**
  ```http
  Content-Type: application/json
  Authorization: Bearer <token>
  X-Request-ID: <uuidv4-string>
  ```
- **Xác thực:** Bearer Token. Trong môi trường kiểm thử/phát triển, sử dụng các token định sẵn:
  - `token-admin`: Vai trò `admin`, `analyst`, `operator` (User ID: `11111111-1111-1111-1111-111111111111`).
  - `token-analyst`: Vai trò `analyst`, `operator` (User ID: `22222222-2222-2222-2222-222222222222`).
  - `token-evaluator`: Vai trò `evaluator` (User ID: `33333333-3333-3333-3333-333333333333`).
  - `token-operator`: Vai trò `operator` (User ID: `44444444-4444-4444-4444-444444444444`).

### 2.2. Cấu trúc Phong bì Lỗi Chuẩn (Standard Error Envelope)
Mọi phản hồi lỗi (4xx, 5xx) từ Backend đều tuân thủ 100% cấu trúc:
```json
{
  "detail": {
    "code": "XS_CANONICAL_ERROR_CODE",
    "message": "Mô tả chi tiết nguyên nhân lỗi bằng tiếng Anh kỹ thuật rõ ràng",
    "advisory_only": true
  }
}
```
*(Lưu ý: Khóa `advisory_only: true` xuất hiện trên toàn bộ các lỗi liên quan đến phân hệ Jev AI).*

---

## 3. CHI TIẾT ĐẶC TẢ TỪNG ENDPOINT

---

### API-01: GET `/health` — Service Liveness Probe
- **Mục đích:** Kiểm tra trạng thái sống còn của tiến trình Backend.
- **Xác thực:** Không (Public).
- **Phản hồi 200 OK:**
```json
{
  "status": "ok",
  "service": "x-sentinel",
  "version": "v3",
  "demo_mode": true,
  "jev_ai_enabled": false
}
```
- **Frontend Usage:** Dùng cho thanh trạng thái Footer hoặc ping kiểm tra kết nối nền.

---

### API-02: GET `/ready` — Platform Readiness Probe & Blocker Catalog
- **Mục đích:** Đánh giá tính sẵn sàng của toàn hệ thống trước khi cho phép người dùng thao tác.
- **Xác thực:** Không (Public).
- **Phản hồi 200 OK (Sẵn sàng):**
```json
{
  "status": "ready",
  "demo_mode": true,
  "scientific_ready": false,
  "database": {
    "ok": true,
    "status": "connected",
    "current_revision": "0002_v3_jev_ai_audit",
    "expected_revision": "0002_v3_jev_ai_audit",
    "revision_status": "MATCH"
  },
  "jev_ai": {
    "enabled": false,
    "status": "disabled",
    "advisory_only": true,
    "model_id": null,
    "prompt_version": "jev-v3.0.0",
    "endpoint_label": "lm_studio_local",
    "readiness_blocking": false,
    "error": null
  },
  "blockers": []
}
```
- **Phản hồi 503 Service Unavailable (Chưa sẵn sàng):**
```json
{
  "status": "not_ready",
  "demo_mode": false,
  "scientific_ready": false,
  "database": {
    "ok": false,
    "status": "error",
    "error": "database unavailable or migration revision mismatch"
  },
  "jev_ai": {
    "enabled": true,
    "status": "unavailable",
    "error": "Connection refused to LM Studio"
  },
  "blockers": [
    "freeze view-map/model/M4/fusion configuration",
    "database unavailable or migration revision mismatch"
  ]
}
```
- **Frontend Usage:** Gọi tại App Root khi khởi động ứng dụng. Nếu trả về 503, hiển thị màn hình bảo trì/chờ kèm danh sách `blockers`.

---

### API-03: GET `/v1/config/status` — Non-sensitive Configuration Identity
- **Mục đích:** Cung cấp thông tin môi trường và cấu hình phi nhạy cảm.
- **Xác thực:** Không (Public).
- **Phản hồi 200 OK:**
```json
{
  "environment": "development",
  "demo_mode": true,
  "input_mode": "vector",
  "database_required": true,
  "database_status": "connected",
  "database_revision": "0002_v3_jev_ai_audit",
  "database_revision_status": "MATCH",
  "expected_database_revision": "0002_v3_jev_ai_audit",
  "scientific_config_status": "TBD_MUST_FREEZE",
  "jev_ai": {
    "enabled": true,
    "status": "configured",
    "model_id": "Jev-Style-Qwen3.5-2B-Decision",
    "prompt_version": "jev-v3.0.0",
    "endpoint_label": "lm_studio_local",
    "advisory_only": true,
    "local_only": true
  }
}
```

---

### API-04: GET `/v1/ai/status` — Jev AI LM Studio Status Probe
- **Mục đích:** Thăm dò độc lập trạng thái kết nối tới LM Studio mà không ảnh hưởng tới lõi phát hiện.
- **Xác thực:** Không (Public).
- **Phản hồi 200 OK:**
```json
{
  "enabled": true,
  "status": "available",
  "advisory_only": true,
  "model_id": "Jev-Style-Qwen3.5-2B-Decision",
  "prompt_version": "jev-v3.0.0",
  "endpoint_label": "lm_studio_local",
  "readiness_blocking": false,
  "error": null
}
```

---

### API-05: POST `/v1/analyze/vector` — Core Vector Ingestion & Analysis
- **Mục đích:** Tiếp nhận và phân tích vector đặc trưng EMBER 2.381 chiều, trả về phán quyết và bằng chứng pháp chứng.
- **Xác thực:** Bắt buộc Bearer Token (Quyền: `Operator`, `Analyst`, `Admin`).
- **Request Body (JSON):**
> [!NOTE]
> **Quy cách Vector:** Mảng `features` bắt buộc phải chứa đúng 2.381 số thực hữu hạn (`float`). Không được chứa `string`, `null`, `NaN` hoặc `Infinity`. Ví dụ JSON dưới đây là bản minh họa rút gọn (4 phần tử thay vì 2.381 phần tử) đảm bảo cú pháp JSON hợp lệ có thể parse thực thi:
```json
{
  "features": [0.0125, 0.4502, 12.0, 0.0],
  "source_name": "sample_malware_trojan_test.exe",
  "request_id": "req-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
}
```
*Tạo fixture hợp lệ đầy đủ 2.381 chiều phục vụ kiểm thử:*
- TypeScript: `const features: number[] = Array(2381).fill(0.0125);`
- Python: `features: list[float] = [0.0125] * 2381`
- **Phản hồi 200 OK (Thành công):**
```json
{
  "request_id": "req-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "completed",
  "demo_mode": true,
  "malware_score": 0.8842,
  "signals": {
    "m1": 0.7421,
    "m2": 0.1250,
    "m3": 0.6580,
    "m4": 0.7120,
    "m5": 0.3000
  },
  "suspicion_score": 0.5218,
  "threshold": 0.46885,
  "decision": "ALERT",
  "view_contributions": {
    "structural": 0.1852,
    "behavioral": 0.6214,
    "metadata": 0.1934
  },
  "warnings": [
    "DEMO_MODE_ACTIVE_NOT_SCIENTIFIC_EVIDENCE"
  ],
  "evidence_ref": "41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb",
  "job_id": "c3a88a4e-d621-4d37-884a-952a20b0800e"
}
```
- **Mã lỗi có thể xảy ra:**
  - `401 Unauthorized` (`XS_UNAUTHENTICATED` / `XS_INVALID_CREDENTIALS`): Thiếu hoặc sai token.
  - `403 Forbidden` (`XS_FORBIDDEN`): Tài khoản bị vô hiệu hóa hoặc không đủ quyền.
  - `409 Conflict` (`XS_DUPLICATE_REQUEST`): Trùng `request_id` đã được phân tích trước đó.
  - `422 Unprocessable Entity` (`XS_INPUT_INVALID`): Vector không đúng 2.381 chiều hoặc chứa NaN/Infinity.
  - `429 Too Many Requests` (`XS_DETECTOR_OVERLOADED`): Hệ thống vượt mức 50 yêu cầu đồng thời.
  - `500 Internal Server Error` (`XS_AUDIT_WRITE_FAILED`): Ghi tệp bằng chứng thất bại.

---

### API-06: POST `/v1/analyze/file` — Binary File Ingestion (Gated Phase 2)
- **Mục đích:** Cổng nạp tệp PE thô (bị khóa an toàn kiểu đóng).
- **Phản hồi 501 Not Implemented:**
```json
{
  "detail": {
    "code": "XS_FEATURE_DISABLED",
    "message": "raw PE/LIEF is Phase 2"
  }
}
```

---

### API-07: GET `/v1/analysis` — List Analysis History with Pagination
- **Mục đích:** Tra cứu lịch sử phân tích với bộ lọc đa tiêu chí và phân trang.
- **Xác thực:** Bắt buộc (Quyền: `Operator`, `Analyst`, `Evaluator`, `Admin`).
- **Query Parameters:**
  - `limit`: `int` (1 – 1.000, mặc định 50).
  - `offset`: `int` ($\ge 0$, mặc định 0).
  - `status`: `string` (`queued`, `running`, `completed`, `failed`, `quarantined`).
  - `decision`: `string` (`pass`, `alert`, `quarantine`).
  - `input_mode`: `string` (`vector`, `raw_pe`).
  - `demo_mode`: `boolean` (`true`, `false`).
- **Phản hồi 200 OK:**
```json
{
  "items": [
    {
      "id": "c3a88a4e-d621-4d37-884a-952a20b0800e",
      "request_id": "req-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "status": "completed",
      "input_mode": "vector",
      "demo_mode": true,
      "decision": "alert",
      "malware_score": 0.8842,
      "suspicion_score": 0.5218,
      "created_at": "2026-10-16T08:30:00+00:00",
      "completed_at": "2026-10-16T08:30:01.250+00:00"
    }
  ],
  "total": 142,
  "limit": 50,
  "offset": 0
}
```

---

### API-08: GET `/v1/analysis/{analysis_id}` — Get Analysis Forensic Detail
- **Mục đích:** Lấy toàn bộ cây dữ liệu chi tiết của một bản ghi phân tích bao gồm M1–M5, cảnh báo và thời gian thực thi.
- **Xác thực:** Bắt buộc (Bảo vệ quyền sở hữu BOLA/IDOR).
- **Path Parameter:** `analysis_id` (UUID hoặc chuỗi `request_id`).
- **Phản hồi 200 OK:**
```json
{
  "id": "c3a88a4e-d621-4d37-884a-952a20b0800e",
  "request_id": "req-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "completed",
  "input_mode": "vector",
  "input_sha256": "41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb",
  "demo_mode": true,
  "created_at": "2026-10-16T08:30:00+00:00",
  "completed_at": "2026-10-16T08:30:01.250+00:00",
  "error_code": null,
  "error_message": null,
  "result": {
    "malware_score": 0.8842,
    "suspicion_score": 0.5218,
    "threshold": 0.46885,
    "decision": "alert",
    "latency_ms": 1250.4,
    "view_contributions": {
      "structural": 0.1852,
      "behavioral": 0.6214,
      "metadata": 0.1934
    },
    "evidence_uri": "artifacts/audit/events.jsonl",
    "result_json": {}
  },
  "scores": [
    {
      "detector_code": "M1",
      "score": 0.7421,
      "diagnostics": { "top_k_mass": 0.621 }
    },
    {
      "detector_code": "M2",
      "score": 0.1250,
      "diagnostics": { "mean_entropy": 0.842 }
    },
    {
      "detector_code": "M3",
      "score": 0.6580,
      "diagnostics": { "dominant_view": "behavioral" }
    },
    {
      "detector_code": "M4",
      "score": 0.7120,
      "diagnostics": { "discrepancy": 0.436 }
    },
    {
      "detector_code": "M5",
      "score": 0.3000,
      "diagnostics": { "violations": 1 }
    }
  ],
  "alerts": [
    {
      "id": "e4f5a6b7-8901-2345-6789-abcdef012345",
      "analysis_job_id": "c3a88a4e-d621-4d37-884a-952a20b0800e",
      "severity": "high",
      "status": "open",
      "reason": "M4 Cross-View discrepancy detected potential evasion trigger",
      "created_at": "2026-10-16T08:30:01+00:00",
      "resolved_at": null
    }
  ],
  "evidence_ref": "41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb"
}
```
- **Mã lỗi:**
  - `403 Forbidden` (`XS_FORBIDDEN`): Bản ghi thuộc sở hữu của người dùng khác.
  - `404 Not Found` (`XS_ANALYSIS_NOT_FOUND`): Không tìm thấy bản ghi.

---

### API-09: GET `/v1/analysis/{analysis_id}/evidence` — Get Verified Canonical Evidence
- **Mục đích:** Lấy gói bằng chứng pháp chứng 19 trường kèm kiểm tra toàn vẹn băm RFC 8785 theo thời gian thực.
- **Xác thực:** Bắt buộc (Quyền: `Analyst`, `Evaluator`, `Admin`).
- **Phản hồi 200 OK:**
```json
{
  "request_id": "req-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "run_id": "run-f1e2d3c4-b5a6-7890-1234-56789abcdef0",
  "timestamp": "2026-10-16T08:30:01.200Z",
  "code_commit": "git_commit_hash_v3_canonical_0002",
  "build_digest": "sha256:build_digest_x_sentinel_v3_baseline",
  "input_id": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
  "input_mode": "vector",
  "view_map_hash": "276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
  "model_hash": "509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
  "model_config_hash": "a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
  "detector_config_hash": "f6e5d4c3b2a10987654321fedcba0987654321fedcba0987654321fedcba0987",
  "seed": 42,
  "malware_score": 0.8842,
  "signals": {
    "m1": 0.7421,
    "m2": 0.1250,
    "m3": 0.6580,
    "m4": 0.7120,
    "m5": 0.3000
  },
  "fusion_score": 0.5218,
  "threshold_id": "tau_d1_calibration_v1",
  "decision": "ALERT",
  "latency_ms": {
    "end_to_end": 1250.4,
    "model": 3.42,
    "signals": 1240.1,
    "fusion": 0.85,
    "input_validation": 0.25
  },
  "demo_mode": true,
  "evidence_hash": "41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb",
  "verified": true
}
```
- **Mã lỗi đặc thù:**
  - `409 Conflict` (`XS_EVIDENCE_INTEGRITY_MISMATCH`): Phát hiện tệp bằng chứng đã bị sửa đổi trái phép sau khi ghi.

---

### API-10: GET `/v1/alerts` — List SOC Alerts with Filtering
- **Mục đích:** Xem danh sách cảnh báo an ninh cần chuyên viên SOC xử lý.
- **Xác thực:** Bắt buộc (Quyền: `Operator`, `Analyst`, `Admin`).
- **Query Parameters:** `limit`, `offset`, `severity` (`low`, `medium`, `high`, `critical`), `status` (`open`, `acknowledged`, `resolved`, `dismissed`), `analysis_job_id`.
- **Phản hồi 200 OK:**
```json
{
  "items": [
    {
      "id": "e4f5a6b7-8901-2345-6789-abcdef012345",
      "analysis_job_id": "c3a88a4e-d621-4d37-884a-952a20b0800e",
      "severity": "high",
      "status": "open",
      "reason": "M4 Cross-View discrepancy detected potential evasion trigger",
      "created_at": "2026-10-16T08:30:01+00:00",
      "resolved_at": null
    }
  ],
  "total": 18,
  "limit": 50,
  "offset": 0
}
```

---

### API-11: GET `/v1/alerts/{alert_id}` — Get Single Alert Detail
- **Mục đích:** Xem chi tiết một cảnh báo.
- **Xác thực:** Bắt buộc.
- **Phản hồi 200 OK:** Trả về đối tượng `AlertSummary` như trong danh sách.

---

### API-12: PATCH `/v1/alerts/{alert_id}` — Update Alert Lifecycle Status
- **Mục đích:** Thay đổi trạng thái xử lý của cảnh báo và ghi nhật ký kiểm toán `audit_events`.
- **Xác thực:** Bắt buộc (Quyền: `Analyst`, `Admin`). Vai trò `Operator` bị cấm.
- **Request Body (JSON):**
```json
{
  "status": "acknowledged"
}
```
*(Các giá trị hợp lệ: `acknowledged`, `resolved`, `dismissed`).*
- **Phản hồi 200 OK:** Trả về `AlertSummary` đã cập nhật.
- **Mã lỗi:**
  - `400 Bad Request` (`XS_INVALID_TRANSITION`): Trạng thái không hợp lệ.
  - `403 Forbidden` (`XS_FORBIDDEN`): Operator không có quyền cập nhật.
  - `404 Not Found` (`XS_ALERT_NOT_FOUND`): Không tìm thấy Alert.

---

### API-13: POST `/v1/ai/explain` — Execute Jev AI Advisory Workflow
- **Mục đích:** Kích hoạt mô hình Jev AI cục bộ để phân tích, giải thích hoặc soạn báo cáo.
- **Xác thực:** Bắt buộc (Quyền: `Analyst`, `Admin`).
- **Request Body (JSON):**
```json
{
  "analysis_id": "c3a88a4e-d621-4d37-884a-952a20b0800e",
  "mode": "explain",
  "compare_with_analysis_id": null,
  "focus_signals": ["m1", "m4"],
  "question": "Vì sao mẫu này bị cảnh báo bất đồng thuận giữa các view?"
}
```
*(Các chế độ `mode` hỗ trợ: `explain`, `triage`, `compare`, `report`).*
- **Phản hồi 200 OK (Thành công):**
```json
{
  "id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "analysis_job_id": "c3a88a4e-d621-4d37-884a-952a20b0800e",
  "requested_by_user_id": "22222222-2222-2222-2222-222222222222",
  "mode": "explain",
  "status": "completed",
  "advisory_only": true,
  "authoritative_decision_unchanged": true,
  "model_id": "Jev-Style-Qwen3.5-2B-Decision",
  "endpoint_label": "lm_studio_local",
  "prompt_version": "jev-v3.0.0",
  "input_digest_sha256": "8f4e2b1a9c3d5e7f0a2b4c6e8f1a3b5c7e9f0a2b4c6e8f1a3b5c7e9f0a2b4c6e",
  "output_digest_sha256": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
  "context_summary": {
    "features_count": 2381,
    "top_signals": ["m1", "m4"],
    "decision": "ALERT"
  },
  "response_text": "### Phân tích Cố vấn Kỹ thuật (Jev AI)\n\nMẫu phân tích mang mã băm kết quả `418182...` kích hoạt cảnh báo do tín hiệu **M4 (Cross-View Disagreement)** đạt giá trị 0.7120. Điều này chỉ ra rằng góc nhìn Hành vi (Behavioral View) đóng góp tới 62.14% thuộc tính nhưng mô hình suy diễn tổng thể chỉ ra sự bất đồng thuận với cấu trúc PE tĩnh.\n\n**Khuyến nghị SOC:**\n1. Kiểm tra bảng Imports xem có kỹ thuật API Hashing né tránh chữ ký tĩnh hay không.\n2. Thực hiện cách ly mẫu vào Sandbox để phân tích hành vi động.",
  "decision_result": {
    "choice": "BACKDOOR_SUSPECTED",
    "probabilities": {
      "BACKDOOR_SUSPECTED": 0.942,
      "CLEAN": 0.058
    }
  },
  "latency_ms": 2340.5,
  "error_code": null,
  "error_message": null,
  "created_at": "2026-10-16T08:35:00+00:00",
  "completed_at": "2026-10-16T08:35:02.340+00:00"
}
```
- **Mã lỗi đặc thù:**
  - `422 Unprocessable Entity` (`XS_AI_CONTEXT_BLOCKED`): Phát hiện prompt injection trong câu hỏi.
  - `429 Too Many Requests` (`XS_AI_OVERLOADED`): Hàng đợi AI vượt quá 16 tác vụ.
  - `503 Service Unavailable` (`XS_AI_DISABLED` hoặc `XS_AI_UNAVAILABLE`): LM Studio offline.
  - `504 Gateway Timeout` (`XS_AI_TIMEOUT`): LM Studio không phản hồi sau 60s.

---

### API-14: GET `/v1/ai/runs` — List Jev AI Advisory Runs
- **Mục đích:** Xem lịch sử các lần chạy suy luận của Jev AI.
- **Xác thực:** Bắt buộc (Quyền: `Analyst`, `Admin`).
- **Query Parameters:** `analysis_id`, `mode`, `status`, `limit`, `offset`.
- **Phản hồi 200 OK:**
```json
{
  "items": [
    {
      "id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
      "analysis_job_id": "c3a88a4e-d621-4d37-884a-952a20b0800e",
      "requested_by_user_id": "22222222-2222-2222-2222-222222222222",
      "mode": "explain",
      "status": "completed",
      "advisory_only": true,
      "authoritative_decision_unchanged": true,
      "model_id": "Jev-Style-Qwen3.5-2B-Decision",
      "endpoint_label": "lm_studio_local",
      "prompt_version": "jev-v3.0.0",
      "input_digest_sha256": "8f4e2b1a9c3d5e7f0a2b4c6e8f1a3b5c7e9f0a2b4c6e8f1a3b5c7e9f0a2b4c6e",
      "output_digest_sha256": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
      "context_summary": {},
      "response_text": "...",
      "decision_result": null,
      "latency_ms": 2340.5,
      "error_code": null,
      "error_message": null,
      "created_at": "2026-10-16T08:35:00+00:00",
      "completed_at": "2026-10-16T08:35:02.340+00:00"
    }
  ],
  "total": 35,
  "limit": 50,
  "offset": 0
}
```

---

### API-15: GET `/v1/ai/runs/{run_id}` — Get Jev AI Run Detail
- **Mục đích:** Xem chi tiết một lần chạy AI cụ thể.
- **Xác thực:** Bắt buộc (Bảo vệ quyền sở hữu BOLA/IDOR).
- **Phản hồi 200 OK:** Trả về đối tượng `JevAIRunResponse`.

---

### API-16: POST `/v1/ai/runs/{run_id}/feedback` — Record Analyst Feedback
- **Mục đích:** Gửi đánh giá chuyên viên cho một lượt chạy AI đã kết thúc.
- **Xác thực:** Bắt buộc (Quyền: `Analyst`, `Admin`).
- **Request Body (JSON):**
```json
{
  "rating": 5,
  "label": "helpful",
  "comment": "Giải thích rất sát với dấu hiệu bất thường của view hành vi."
}
```
*(Quy tắc: `rating` là số nguyên nghiêm ngặt từ 1 đến 5; `label` chọn từ: `helpful`, `not_helpful`, `incorrect`, `unsafe`, `unclear`; `comment` tối đa 2.000 ký tự).*
- **Phản hồi 201 Created:**
```json
{
  "id": "3b4c5d6e-7f8a-9b0c-1d2e-3f4a5b6c7d8e",
  "jev_ai_run_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "user_id": "22222222-2222-2222-2222-222222222222",
  "rating": 5,
  "label": "helpful",
  "comment": "Giải thích rất sát với dấu hiệu bất thường của view hành vi.",
  "advisory_only": true,
  "created_at": "2026-10-16T08:36:12+00:00"
}
```
- **Mã lỗi:**
  - `400 Bad Request` (`XS_FEEDBACK_INVALID`): Vi phạm validation.
  - `409 Conflict` (`XS_AI_RUN_NOT_TERMINAL`): Lượt chạy AI chưa kết thúc.
  - `409 Conflict` (`XS_DUPLICATE_FEEDBACK`): Người dùng đã đánh giá lượt chạy này rồi.

---

### API-17: GET `/v1/ai/runs/{run_id}/feedback` — List Feedback Records
- **Mục đích:** Xem các đánh giá phản hồi đã gửi của một lượt chạy AI.
- **Xác thực:** Bắt buộc.
- **Phản hồi 200 OK:**
```json
{
  "jev_ai_run_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "total": 1,
  "items": [
    {
      "id": "3b4c5d6e-7f8a-9b0c-1d2e-3f4a5b6c7d8e",
      "jev_ai_run_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
      "user_id": "22222222-2222-2222-2222-222222222222",
      "rating": 5,
      "label": "helpful",
      "comment": "Giải thích rất sát...",
      "advisory_only": true,
      "created_at": "2026-10-16T08:36:12+00:00"
    }
  ]
}
```

---

### API-18: POST `/v1/ai/docs/ask` — Docs QA (Gated Phase 2)
- **Mục đích:** Hỏi đáp tài liệu qua AI (bị khóa an toàn kiểu đóng).
- **Phản hồi 501 Not Implemented:**
```json
{
  "detail": {
    "code": "XS_FEATURE_DISABLED",
    "message": "Documentation QA (/v1/ai/docs/ask) is gated for Phase 2",
    "advisory_only": true
  }
}
```

---

### API-19: GET `/v1/system/telemetry` — Authentic Telemetry (`include_in_schema=False`)
- **Mục đích:** Lấy thông số đo lường hiệu năng thực tế từ hệ điều hành qua `psutil` (CPU, Virtual Memory, Process RSS/VMS/Threads). Endpoint này bị ẩn khỏi OpenAPI (`include_in_schema=False`).
- **Xác thực:** Bắt buộc (Quyền: `Operator`, `Admin`).
- **Phản hồi 200 OK (`/v1/system/telemetry`):**
```json
{
  "status": "ok",
  "cpu": {
    "utilization_percent": 14.8,
    "logical_cores": 8,
    "physical_cores": 8
  },
  "memory": {
    "total_bytes": 17098485760,
    "available_bytes": 8452145152,
    "used_bytes": 8646340608,
    "used_percent": 50.6
  },
  "process": {
    "pid": 14220,
    "rss_bytes": 220012544,
    "vms_bytes": 654215168,
    "thread_count": 12
  }
}
```
- **Phản hồi khi suy giảm (Degraded State):**
```json
{
  "status": "degraded",
  "error": "Failed to collect authentic system telemetry: <chi tiết lỗi OS>"
}
```

---

### API-20: GET `/v1/system/metrics` — Authenticated Prometheus Exposition (`include_in_schema=False`)
- **Mục đích:** Thu thập số liệu hiệu năng hệ thống định dạng Prometheus Text Exposition (`text/plain; version=0.0.4; charset=utf-8`). Nếu `settings.metrics_export_enabled == False`, trả về 404 `XS_FEATURE_DISABLED`. Endpoint này bị ẩn khỏi OpenAPI (`include_in_schema=False`).
- **Xác thực:** Bắt buộc (Quyền: `Operator`, `Admin`).
- **Phản hồi 200 OK:**
```text
# HELP api_requests_total Total count of handled API requests
# TYPE api_requests_total counter
api_requests_total{endpoint="/v1/analyze/vector",method="POST",status_code="200"} 124.0
# HELP api_request_latency_ms API request latency in milliseconds
# TYPE api_request_latency_ms histogram
api_request_latency_ms_bucket{endpoint="/v1/analyze/vector",le="50.0",method="POST",status_code="200"} 85.0
```

---

### API-21: GET `/metrics` — Public Prometheus Scrape Endpoint (`include_in_schema=False`)
- **Mục đích:** Endpoint cào số liệu Prometheus tiêu chuẩn tại root path cho hạ tầng giám sát nội bộ (Prometheus server / VictoriaMetrics). Nếu `settings.metrics_export_enabled == False`, trả về 404 `XS_FEATURE_DISABLED`. Endpoint này bị ẩn khỏi OpenAPI (`include_in_schema=False`).
- **Xác thực:** Không (Public).
- **Phản hồi 200 OK:**
```text
# HELP api_requests_total Total count of handled API requests
# TYPE api_requests_total counter
api_requests_total{endpoint="/v1/analyze/vector",method="POST",status_code="200"} 124.0
# HELP api_request_latency_ms API request latency in milliseconds
# TYPE api_request_latency_ms histogram
api_request_latency_ms_bucket{endpoint="/v1/analyze/vector",le="50.0",method="POST",status_code="200"} 85.0
```

---

## 4. BẢNG ÁNH XẠ TOÀN DIỆN: TƯƠNG TÁC FRONTEND → API → BACKEND SERVICE → CSDL

| Hành động Người dùng trên UI | API Endpoint | Phương thức | Backend Service chịu trách nhiệm | Thực thể CSDL tác động | Phản hồi Frontend nhận được |
|---|---|:---:|---|---|---|
| Nhấn "Analyze" trên form vector | `/v1/analyze/vector` | `POST` | `AnalysisService.analyze_vector` | `analysis_jobs`, `analysis_results`, `detector_scores`, `alerts`, `artifacts` | `AnalysisResponse` (Verdict, Điểm, 3-View, M1-M5) |
| Chuyển trang trong bảng Lịch sử | `/v1/analysis` | `GET` | `HistoryService.list_history` | Đọc `analysis_jobs` kết hợp `analysis_results` | `AnalysisHistoryListResponse` (Danh sách tóm tắt) |
| Nhấp xem chi tiết một bản ghi | `/v1/analysis/{id}` | `GET` | `HistoryService.get_analysis_detail` | Đọc `analysis_jobs`, `detector_scores`, `alerts` | `AnalysisDetailResponse` (Toàn bộ forensic metrics) |
| Nhấn nút "Tải Bằng chứng JSON" | `/v1/analysis/{id}/evidence` | `GET` | `EvidenceService.get_canonical_evidence`| Đọc `artifacts` + tệp `.jsonl` | `CanonicalEvidenceResponse` (19 trường + băm SHA-256) |
| Lọc cảnh báo SOC theo mức độ | `/v1/alerts` | `GET` | `AlertService.list_alerts` | Đọc `alerts` | `AlertListResponse` (Danh sách cảnh báo) |
| Nhấn nút "Acknowledge" cảnh báo | `/v1/alerts/{id}` | `PATCH` | `AlertService.update_alert_status` | Cập nhật `alerts`, ghi `audit_events` | `AlertSummary` (Trạng thái mới: `acknowledged`) |
| Nhấn "Explain with Jev AI" | `/v1/ai/explain` | `POST` | `JevAIService.execute_workflow` | Ghi `jev_ai_runs` (Hai pha không khóa DB) | `JevAIRunResponse` (Văn bản cố vấn & Logprobs) |
| Gửi đánh giá 5 sao cho AI | `/v1/ai/runs/{id}/feedback`| `POST` | `JevAIService.submit_feedback` | Ghi `jev_ai_feedback` | `JevFeedbackResponse` (Xác nhận đã ghi nhận) |
| Mở trang Giám sát Hệ thống | `/health` & `/ready` | `GET` | Controller trong `main.py` | Kiểm tra kết nối DB & phiên bản Alembic | JSON trạng thái, cờ demo mode, danh sách blocker |
| Mở tab Phần cứng Telemetry | `/v1/system/telemetry` | `GET` | `infrastructure.monitoring.telemetry`| Đọc trực tiếp từ OS qua `psutil` | Thống kê CPU, RAM, tiến trình thực |
| Giám sát Prometheus Scrape | `/v1/system/metrics`, `/metrics` | `GET` | `infrastructure.monitoring.metrics` | Đọc registry bộ đếm Prometheus trong bộ nhớ | Dữ liệu metric định dạng Prometheus text |
