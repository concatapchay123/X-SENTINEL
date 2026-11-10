# X-SENTINEL V3 — KẾ HOẠCH KHẮC PHỤC KỸ THUẬT TOÀN DIỆN (FULL-SCALE REMEDIATION PLAN)

**Dự án:** X-SENTINEL (Cross-View Backdoor Malware Detection Platform)  
**Thời điểm phê duyệt:** 10/11/2026  
**Commit cơ sở:** `bb92effa7ae88a54381eca91b6cc567c73a0eccb`  
**Trạng thái kế hoạch:** ĐÃ TRIỂN KHAI VÀ XÁC MINH (IMPLEMENTED & VERIFIED)  
**Tài liệu đầu vào bắt buộc:** `G:\IAM301t\X-SENTINEL-audit\AUDIT_REPORT_VI.md` (18 phát hiện F01–F18)

---

## 1. MỤC TIÊU & NGUYÊN TẮC BẤT BIẾN (ENGINEERING INVARIANTS)

Đợt remediation toàn diện này được thực hiện theo 7 nguyên tắc kỹ thuật không thể thỏa hiệp:
1. **Read before edit:** Khảo sát toàn diện 18 phát hiện trong báo cáo audit, xác định chính xác nguyên nhân gốc (root-cause), không sửa chữa theo phỏng đoán.
2. **Preserve existing functionality:** Bảo toàn 100% các public API contracts, không thay đổi request/response schemas hợp lệ, bảo toàn detection semantics và tính toán SHAP/Fusion.
3. **No fake fixes:** Nghiêm cấm hardcode kết quả, không xóa test thất bại, không tắt lint/mypy/security gates, fail-closed khi thiếu tài nguyên cốt lõi.
4. **Minimal and justified changes:** Trực tiếp giải quyết nguyên nhân gốc rễ, áp dụng tư duy tối giản Senior YAGNI, không tạo abstraction thừa thãi.
5. **Data safety:** Không reset dữ liệu, không xóa bỏ models, không làm thất thoát audit logs hoặc tài liệu nghiên cứu.
6. **Git safety:** Thực hiện kỹ lưỡng trên local workspace, không tự ý push hay force push lên remote repository khi chưa có lệnh.
7. **Verify every claim:** Chỉ tuyên bố một vấn đề là FIXED khi có kiểm thử tự động xác minh thực tế, chạy thành công với evidence rõ ràng.

---

## 2. MA TRẬN 18 PHÁT HIỆN & PHÂN NHÓM XỬ LÝ (REMEDIATION MATRIX)

| ID | Mức độ | Thành phần | Tóm tắt nguyên nhân gốc | Giải pháp kỹ thuật | Regression Test | Trạng thái |
|:---|:---|:---|:---|:---|:---|:---:|
| **F01** | P1 | Security / Auth | `api_auth_mode=none` và predefined tokens được chấp nhận trong production; anonymous user có quyền admin | Cấm `none` và test tokens khi `env="production"`; Anonymous có roles rỗng; `is_admin` trả False cho anonymous | `tests/security/test_f01_f03_auth_idor_regression.py` | **FIXED_VERIFIED** |
| **F02** | P1 | Services / Analysis | Prefix `req-be04-` kích hoạt xóa job cũ của người khác không kiểm tra ownership | Xóa bỏ hoàn toàn nhánh xóa dữ liệu; triển khai idempotency kiểm tra input hash và từ chối 409 | `tests/integration/test_f02_f05_f07_data_integrity.py` | **FIXED_VERIFIED** |
| **F03** | P1 | Security / Alert | Alert API thiếu kiểm tra quyền sở hữu tương ứng AnalysisJob; Analyst A xem/sửa được alert của Analyst B | Truyền `user` vào service; `assert_alert_ownership` đối chiếu `job.user_id == user.user_id` | `tests/security/test_f01_f03_auth_idor_regression.py` | **FIXED_VERIFIED** |
| **F04** | P1 | Scripts / Release | `verify_release_tuple.py` báo VERIFIED dù không có Docker daemon và model weights; checklist in PASS ảo | Báo cáo đúng `UNAVAILABLE`/`DRAFT`; thêm chế độ strict fail-closed (exit 1) khi thiếu artifact | `tests/release/test_f04_f11_f12_release_ci.py` | **FIXED_VERIFIED** |
| **F05** | P1 | Services / Transaction | DB commit trước khi ghi file audit JSONL; lỗi ghi file gây bất nhất trạng thái | Bọc `audit.append` an toàn không làm hỏng DB transaction đã commit; DB là nguồn sự thật chính | `tests/integration/test_f02_f05_f07_data_integrity.py` | **FIXED_VERIFIED** |
| **F06** | P2 | Evidence / Provenance | `CanonicalEvidence` ghi cứng commit SHA và hashes cấu hình giả lập | Tính toán dynamic provenance từ git commit thật, sha256 cấu hình và weights thật | `tests/detection/test_f06_f08_detection_pipeline_and_provenance.py` | **FIXED_VERIFIED** |
| **F07** | P2 | Domain / Serialization | `round(f, 6)` trước khi hash làm 2 vector khác nhau ở 1e-7 có cùng SHA-256 digest | Sử dụng `struct.pack(f"<{len(v)}f", *v)` tuần tự hóa chuẩn IEEE 754 không làm tròn mất dữ liệu | `tests/integration/test_f02_f05_f07_data_integrity.py` | **FIXED_VERIFIED** |
| **F08** | P1 | Core / Detection | API chỉ chạy DemoModelService; M2/M4/M5 bị gán 0; scientific mode ném uncaught RuntimeError | Tích hợp `DetectorPipeline` tính đủ M1–M5; Scientific mode fail-closed với HTTP 503 `XS_SCIENTIFIC_UNAVAILABLE` | `tests/detection/test_f06_f08_detection_pipeline_and_provenance.py` | **FIXED_VERIFIED** |
| **F09** | P2 | Monitoring / Metrics | URL lạ/404 dùng raw path làm endpoint label; Prometheus dict tăng bộ nhớ $O(N)$ không giới hạn | Chuẩn hóa endpoint theo route template; mọi URL lạ/404 gán `"unmatched"`; giới hạn max 500 series | `tests/observability/test_f09_metrics_cardinality.py` | **FIXED_VERIFIED** |
| **F10** | P2 | Services / Telemetry | `end_to_end` latency dừng trước giai đoạn DB persistence và audit flush | Mở rộng timer đo toàn bộ request lifecycle (input, model, signals, fusion, persistence, audit) | `tests/integration/test_f02_f05_f07_data_integrity.py` | **FIXED_VERIFIED** |
| **F11** | P1 | Infrastructure / Docker | `docker-compose.yml` service migrate chạy alembic ngay mà không tạo database xsentinel | Thêm `python scripts/ensure_database.py &&` trước lệnh alembic trong migrate service | `tests/release/test_f04_f11_f12_release_ci.py` | **FIXED_VERIFIED** |
| **F12** | P1 | CI/CD / Pipeline | CI workflow chỉ cài unixodbc-dev, thiếu `msodbcsql17` làm hỏng kết nối SQL Server tại Gate 3 | Cập nhật `.github/workflows/ci.yml` bổ sung kho Microsoft và cài đặt `msodbcsql17` | `tests/release/test_f04_f11_f12_release_ci.py` | **FIXED_VERIFIED** |
| **F13** | P2 | Packaging / Docker | pyproject.toml gộp tất cả dependency; frontend cài ML/DB; backend cài Streamlit | Tách `[project.optional-dependencies]` thành `ui`, `dev`; Dockerfile frontend chỉ cài `.[ui]` | `scripts/validate_v3_package.py` | **FIXED_VERIFIED** |
| **F14** | P2 | API / Schema | Pydantic không strict ép kiểu bool `True -> 1.0`, string `"1.25" -> 1.25`, vô hiệu hóa validation domain | Thêm `ConfigDict(strict=True)` và field_validator từ chối bool/string, ép kiểm tra độ dài 2.381 | `tests/integration/test_f02_f05_f07_data_integrity.py` | **FIXED_VERIFIED** |
| **F15** | P2 | Frontend / Security | Frontend Streamlit không gửi token xác thực, bị 401 khi bật auth | Thêm env `XS_API_BEARER_TOKEN`, sidebar auth token, gắn header Authorization và xử lý 401/403 | `tests/security/test_f01_f03_auth_idor_regression.py` | **FIXED_VERIFIED** |
| **F16** | P2 | Git / Packaging | Thiếu `.gitattributes` chuẩn hóa line ending; nguy cơ CRLF làm hỏng bash script trong container | Tạo `.gitattributes` ép `* text=auto eol=lf` và `*.sh text eol=lf` | `tests/release/test_f04_f11_f12_release_ci.py` | **FIXED_VERIFIED** |
| **F17** | P2 | Testing / Concurrency | Test concurrency dùng chung SQLite connection/session gây xung đột cursor và thiếu ổn định | Sử dụng session độc lập trên từng worker thread và cô lập file-based SQLite database | `tests/integration/test_be16_database_resilience.py` (10/10 PASS) | **FIXED_VERIFIED** |
| **F18** | P2 | Performance / Layout | `load_view_map` đọc và parse lại YAML trên mỗi request gây chi phí I/O lặp | Áp dụng `@functools.lru_cache(maxsize=8)` trên đường dẫn view map đã resolve | `tests/observability/test_f09_metrics_cardinality.py` | **FIXED_VERIFIED** |

---

## 3. PHÂN KỲ TRIỂN KHAI & PHỐI HỢP CÁC BATCH

Kế hoạch được chia thành 6 đợt triển khai dứt khoát:
- **Batch A (P1 Security Hardening):** Xử lý F01 (Default Deny Auth), F03 (Alert IDOR / Object Ownership), F15 (Frontend Auth Integration).
- **Batch B (Data Integrity & Transactions):** Xử lý F02 (Xóa bỏ prefix destructive), F05 (Atomicity DB/Audit), F07 (Canonical Float Packing), F10 (End-to-End Latency Scope), F14 (Strict Type Validation).
- **Batch C (Release Verification & CI/CD):** Xử lý F04 (Fail-closed release tuple), F11 (Idempotent database provisioning trong compose), F12 (Microsoft ODBC Driver 17 trong CI), F16 (LF Gitattributes).
- **Batch D (Detection Core & Scientific Boundaries):** Xử lý F06 (Dynamic Provenance Bundle), F08 (Tích hợp DetectorPipeline M1-M5 và 503 Scientific Guard).
- **Batch E (Reliability & Observability):** Xử lý F09 (Metrics cardinality bound O(1)), F17 (Thread-safe concurrency testing), F18 (LRU ViewMap caching).
- **Batch F (Packaging, Docker & Final Reports):** Xử lý F13 (Tách dependency, tối ưu Dockerfile frontend/backend) và biên soạn bộ 6 báo cáo kỹ thuật.
