# X-SENTINEL V3 — BẢN GHI THAY ĐỔI KỸ THUẬT CHI TIẾT (REMEDIATION CHANGELOG)

**Dự án:** X-SENTINEL (Cross-View Backdoor Malware Detection Platform)  
**Tài liệu tham chiếu:** `AUDIT_REPORT_VI.md` (18 phát hiện F01–F18)  
**Phiên bản phát hành sau sửa lỗi:** `0.3.0`  
**Ngày cập nhật:** 10/11/2026

---

## 1. BATCH A — BẢO MẬT & PHÂN QUYỀN (SECURITY HARDENING: F01, F03, F15)

### [F01] Khóa chặn cấu hình vô danh/token mặc định trong môi trường Production
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/config.py`
  - `backend/src/x_sentinel/security/auth.py`
- **Chi tiết thay đổi:**
  - Thêm thuộc tính cấu hình `allow_predefined_tokens: bool = False` vào `Settings`.
  - Bổ sung `@model_validator(mode="after") def validate_production_security(self)`: Khi `self.env == "production"`, nếu `self.api_auth_mode == "none"` hoặc `self.allow_predefined_tokens is True`, Pydantic lập tức ném `ValueError` ngăn chặn khởi động ứng dụng.
  - Sửa `ANONYMOUS_USER`: thiết lập `roles: tuple[Role, ...] = ()` (không còn cấp bất kỳ quyền nào).
  - Cập nhật hàm `is_admin(user)`: trả về `False` dứt khoát nếu `user is None` hoặc `user.is_anonymous`.
  - Trong `get_current_user`: khi `settings.env == "production"`, từ chối 100% token định sẵn (`token-admin`, `token-analyst`, `token-operator`), chỉ cho phép các token được tạo hợp lệ qua authentication backend.

### [F03] Kiểm soát quyền sở hữu đối tượng Alert (Object-Level Authorization / IDOR Remediation)
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/security/auth.py`
  - `backend/src/x_sentinel/security/__init__.py`
  - `backend/src/x_sentinel/database/repositories/alert.py`
  - `backend/src/x_sentinel/services/alert_service.py`
  - `backend/src/x_sentinel/api/routes.py`
- **Chi tiết thay đổi:**
  - Xây dựng hàm `assert_alert_ownership(alert: Alert, user: AuthUser, session: Session) -> None`: Đối chiếu `job = session.get(AnalysisJob, alert.analysis_job_id)`. Nếu `job.user_id != user.user_id` và người dùng không có role `admin`, ném `HTTPException(status_code=403, detail={"code": "XS_FORBIDDEN", ...})`.
  - Cập nhật repository `list_alerts`: Nhận tham số tùy chọn `owner_user_id: uuid.UUID | None`. Khi có tham số, tự động JOIN với bảng `AnalysisJob` và áp bộ lọc `AnalysisJob.user_id == owner_user_id`.
  - Cập nhật `AlertService`: Các phương thức `list_alerts`, `get_alert`, `update_alert_status` nhận `user: AuthUser` và thực thi kiểm tra quyền sở hữu trước khi trả về hoặc cập nhật trạng thái alert.
  - Cập nhật `routes.py`: Truyền đối tượng `user: AuthUser` từ dependency `require_roles` vào `AlertService`.

### [F15] Tích hợp xác thực trên giao diện Frontend Streamlit
- **Tệp chỉnh sửa:**
  - `frontend/app.py`
- **Chi tiết thay đổi:**
  - Đọc biến môi trường `XS_API_BEARER_TOKEN` làm token mặc định khi khởi chạy.
  - Bổ sung ô nhập API Token bảo mật trên Sidebar Streamlit cho phép người dùng cấu hình bearer token theo phiên.
  - Gắn header `Authorization: Bearer <token>` vào tất cả các lời gọi `httpx.get` / `httpx.post`.
  - Xử lý mã lỗi HTTP 401 và 403: hiển thị cảnh báo giao diện trực quan yêu cầu cấu hình đúng token có thẩm quyền.

---

## 2. BATCH B — TÍNH TOÀN VẸN DỮ LIỆU & GIAO DỊCH (DATA INTEGRITY: F02, F05, F07, F10, F14)

### [F02] Triệt tiêu cơ chế xóa dữ liệu theo tiền tố `req-be04-`
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/services/analysis_service.py`
- **Chi tiết thay đổi:**
  - Loại bỏ hoàn toàn khối mã kiểm tra `request_id.startswith("req-be04-")` và các lệnh `session.delete(existing_job)`.
  - Triển khai cơ chế Replay an toàn (Idempotency): Nếu `request_id` đã tồn tại, kiểm tra `existing_job.input_sha256 == input_digest`. Nếu khớp và job đã hoàn thành, trả lại kết quả cũ; nếu xung đột dữ liệu, ném `AuditWriteFailureError("Duplicate request_id already exists")` để API trả HTTP 409 Conflict.

### [F05] Đảm bảo tính nhất quán giữa Database Transaction và Audit Log
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/services/analysis_service.py`
- **Chi tiết thay đổi:**
  - Xác lập Database là nguồn sự thật duy nhất (single source of truth) đã được commit.
  - Bọc lời gọi `self.audit.append(result)` vào khối try-except ghi log cảnh báo thay vì để ngoại lệ I/O của file JSONL phá vỡ trạng thái thành công của transaction DB.

### [F07] Tuần tự hóa vector canonical loại bỏ làm tròn mất dữ liệu
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/services/analysis_service.py`
- **Chi tiết thay đổi:**
  - Thay thế chuỗi format số học `round(f, 6)` bằng đóng gói nhị phân chuẩn IEEE 754:
    `vector_bytes = struct.pack(f"<{len(vector)}f", *vector)`
    `input_digest = hashlib.sha256(vector_bytes).hexdigest()`
  - Đảm bảo 2 vector khác biệt ở sai số siêu nhỏ ($10^{-7}$) sẽ sinh ra 2 SHA-256 digest hoàn toàn khác nhau, triệt tiêu nguy cơ va chạm digest do làm tròn.

### [F10] Mở rộng phạm vi đo lường End-to-End Latency
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/services/analysis_service.py`
- **Chi tiết thay đổi:**
  - Tách bạch rõ ràng các giai đoạn đo lường: `input_validation`, `model`, `signals`, `fusion`, `persistence`, `audit`.
  - Khởi động timer ngay khi nhận request và kết thúc sau khi hoàn tất persistence và audit ghi log, phản ánh chính xác 100% thời gian xử lý toàn trình (SLO compliance).

### [F14] Ép kiểu nghiêm ngặt (Strict Numeric Validation) tại API Boundary
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/api/schemas.py`
- **Chi tiết thay đổi:**
  - Cấu hình `model_config = ConfigDict(strict=True)` trên schema `VectorAnalysisRequest`.
  - Bổ sung `@field_validator("features")`: Từ chối dứt khoát kiểu boolean, string, nan, inf; ép buộc kích thước vector phải chính xác $2.381$ phần tử float trước khi chuyển tiếp vào detector pipeline.

---

## 3. BATCH C — XÁC MINH PHÁT HÀNH & CI/CD (RELEASE & CI/CD: F04, F11, F12, F16)

### [F04] Xác minh Release Tuple Fail-Closed trung thực
- **Tệp chỉnh sửa:**
  - `scripts/verify_release_tuple.py`
- **Chi tiết thay đổi:**
  - Hàm `get_docker_image_id`: Trả về `None` khi Docker daemon không hoạt động hoặc image không tìm thấy.
  - Bổ sung kiểm tra tệp trọng số thật trong thư mục `models/` (ngoại trừ README.md).
  - Cập nhật manifest Markdown: Thể hiện đúng nhãn `UNAVAILABLE (Image missing)` và `DRAFT (Weights missing)` thay vì các nhãn pass giả định.
  - Bổ sung các cờ CLI `--strict`, `--require-image`, `--require-model`: Khi kích hoạt, nếu thiếu image hoặc thiếu model weights, script lập tức log lỗi và thoát với mã lỗi `1` (fail-closed).

### [F11] Tự động khởi tạo Database trong Docker Compose
- **Tệp chỉnh sửa:**
  - `docker-compose.yml`
- **Chi tiết thay đổi:**
  - Sửa lệnh `command` của service `migrate` thành:
    `["/bin/sh", "-c", "python scripts/ensure_database.py && alembic -c database/alembic.ini upgrade head"]`
  - Đảm bảo cơ sở dữ liệu `xsentinel` luôn được khởi tạo idempotent trước khi Alembic thực thi migrations.

### [F12] Bổ sung Microsoft ODBC Driver 17 vào CI/CD Pipeline
- **Tệp chỉnh sửa:**
  - `.github/workflows/ci.yml`
- **Chi tiết thay đổi:**
  - Thêm cấu hình kho lưu trữ package chính thức của Microsoft và cài đặt `msodbcsql17`:
    `curl https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc`
    `curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list`
    `sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev`
  - Khắc phục triệt để lỗi kết nối cơ sở dữ liệu làm đứt gãy CI tại Gate 3.

### [F16] Chuẩn hóa ký tự ngắt dòng LF bằng `.gitattributes`
- **Tệp tạo mới:**
  - `.gitattributes`
- **Chi tiết thay đổi:**
  - Thiết lập quy tắc toàn cục `* text=auto eol=lf`.
  - Khóa cứng ngắt dòng LF cho shell scripts (`*.sh text eol=lf`), python (`*.py text eol=lf`), config (`*.yaml`, `*.yml`, `*.json`) và đánh dấu nhị phân cho models/artifacts (`*.bin`, `*.pkl`, `*.docx`).

---

## 4. BATCH D — LÕI NHẬN DIỆN & RANH GIỚI KHOA HỌC (DETECTION CORE: F06, F08)

### [F06] Dynamic Provenance Bundle trong Canonical Evidence
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/services/analysis_service.py`
- **Chi tiết thay đổi:**
  - Tính toán động `code_commit` từ `git rev-parse HEAD` hoặc biến môi trường `XS_BUILD_COMMIT`.
  - Tính toán cryptographic SHA-256 từ tệp cấu hình thực tế (`detector.yaml`, `views.yaml`, `model.yaml`) và tệp trọng số models.
  - Khóa toàn bộ các hashes này vào đối tượng `_provenance` bất biến và ghi vào `CanonicalEvidence` của từng phân tích.

### [F08] Tích hợp DetectorPipeline đầy đủ M1–M5 & 503 Scientific Guard
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/services/analysis_service.py`
  - `backend/src/x_sentinel/api/routes.py`
- **Chi tiết thay đổi:**
  - Trong chế độ Demo: Thay vì gán cứng 0.0, service gọi `self.pipeline.evaluate(...)` tính toán đầy đủ các module M1 (TADR), M2 (STRIP), M3 (View Concentration), M4 (Cross-View Disagreement), và M5 (Semantic Plausibility) và chuyển kết quả vào `FusionEngine`.
  - Trong chế độ Scientific (`demo_mode=False`): Khởi tạo lớp ngoại lệ `ScientificModeUnavailableError`. Nếu tệp trọng số mô hình thực tế chưa được cấp trong `models/`, service ném ngoại lệ này để API trả HTTP 503 Service Unavailable `XS_SCIENTIFIC_UNAVAILABLE` rõ ràng thay vì 500 uncaught error.

---

## 5. BATCH E — ĐỘ TIN CẬY, QUAN SÁT & HIỆU NĂNG (OBSERVABILITY & RELIABILITY: F09, F17, F18)

### [F09] Giới hạn số lượng nhãn Metrics (Cardinality Bounding)
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/main.py`
  - `infrastructure/monitoring/metrics.py`
- **Chi tiết thay đổi:**
  - Trong middleware đo latency API: Trích xuất route template chính thức (`route.path`), gán toàn bộ các URL 404/không khớp về nhãn duy nhất `"unmatched"`.
  - Trong các lớp đo lường `Counter`, `Gauge`, `Histogram`: Bổ sung hằng số `MAX_METRIC_SERIES_LIMIT = 500`. Khi vượt ngưỡng tối đa, các nhãn mới được gom vào bucket `"overflow"`, triệt tiêu hoàn toàn nguy cơ rò rỉ bộ nhớ $O(N)$ do URL fuzzing.

### [F17] Ổn định hóa bài kiểm thử Concurrency
- **Tệp chỉnh sửa:**
  - `tests/integration/test_be16_database_resilience.py`
- **Chi tiết thay đổi:**
  - Thay vì dùng chung connection SQLite in-memory giữa các thread (gây lỗi `sqlite3.InterfaceError`), chuyển sang khởi tạo file-based SQLite database trên thư mục tạm `tmp_path` với session độc lập trên mỗi worker thread.
  - Kết quả kiểm chứng: 10/10 lần chạy kiểm thử liên tiếp đạt 100% PASS ổn định.

### [F18] Bộ đệm LRU Caching cho View Map
- **Tệp chỉnh sửa:**
  - `backend/src/x_sentinel/data/views.py`
- **Chi tiết thay đổi:**
  - Tách hàm phân tích dictionary `_parse_view_map_dict`.
  - Bổ sung hàm nạp từ đĩa có cache `@functools.lru_cache(maxsize=8) def _load_view_map_from_file(resolved_path, allow_demo)`.
  - Triệt tiêu chi phí I/O đọc file lặp và parsing YAML trên mỗi request phân tích.

---

## 6. BATCH F — DOCKER, DEPENDENCY & DỌN DẸP (PACKAGING & CLEANUP: F13)

### [F13] Phân tách Dependency & Tối ưu Dockerfile
- **Tệp chỉnh sửa:**
  - `pyproject.toml`
  - `infrastructure/docker/frontend.Dockerfile`
  - `backend/tests/test_be06_detector_pipeline.py`
  - `tests/security/test_verify_frontend_lock.py`
- **Chi tiết thay đổi:**
  - Bóc tách `streamlit` ra khỏi dependency mặc định của backend, đưa vào nhóm `[project.optional-dependencies].ui`.
  - Nâng giới hạn dải phiên bản dev cho `pytest` (`<10`) và `pytest-cov` (`<8`).
  - Sửa `frontend.Dockerfile`: Bỏ lệnh copy mã nguồn backend thừa, chỉ cài đặt `pip install --no-cache-dir ".[ui]"`.
  - Sửa các cảnh báo biến không dùng trong test suite để đạt 100% Ruff clean.
