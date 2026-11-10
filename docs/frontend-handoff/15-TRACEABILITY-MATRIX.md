# 15 — MA TRẬN TRUY VẾT YÊU CẦU ĐA TẦNG (TRACEABILITY MATRIX)
## HỆ THỐNG X-SENTINEL V3 — MALWARE ANALYSIS & THREAT DETECTION PLATFORM

---

### MỤC LỤC
1. [Nguyên Tắc Thiết Lập Ma Trận Truy Vết (Traceability Design Principles)](#1-nguyên-tắc-thiết-lập-ma-trận-truy-vết-traceability-design-principles)
2. [Bảng Ma Trận Truy Vết Đa Tầng 28 Tính Năng Chuẩn Mực F-01 đến F-28](#2-bảng-ma-trận-truy-vết-đa-tầng-28-tính-năng-chuẩn-mực-f-01-đến-f-28)
   - [Phân Hệ 1: Ingestion & Core Detection (F-01 đến F-10)](#phân-hệ-1-ingestion--core-detection-f-01-đến-f-10)
   - [Phân Hệ 2: Ingestion & Gating Nhị Phân PE (F-11 đến F-12)](#phân-hệ-2-ingestion--gating-nhị-phân-pe-f-11-đến-f-12)
   - [Phân Hệ 3: Bằng Chứng Pháp Chứng & Kiểm Toán Bất Biến (F-13 đến F-15)](#phân-hệ-3-bằng-chứng-pháp-chứng--kiểm-toán-bất-biến-f-13-đến-f-15)
   - [Phân Hệ 4: Lịch Sử Phân Tích & Quản Lý Truy Cập (F-16 đến F-18)](#phân-hệ-4-lịch-sử-phân-tích--quản-lý-truy-cập-f-16-đến-f-18)
   - [Phân Hệ 5: Quản Lý & Tác Chiến Cảnh Báo SOC (F-19 đến F-21)](#phân-hệ-5-quản-lý--tác-chiến-cảnh-báo-soc-f-19-đến-f-21)
   - [Phân Hệ 6: Khuyến Nghị Cố Vấn An Ninh Jev AI (F-22 đến F-25)](#phân-hệ-6-khuyến-nghị-cố-vấn-an-ninh-jev-ai-f-22-đến-f-25)
   - [Phân Hệ 7: Giám Sát Hạ Tầng, Sức Khỏe & Benchmark (F-26 đến F-28)](#phân-hệ-7-giám-sát-hạ-tầng-sức-khỏe--benchmark-f-26-đến-f-28)
3. [Thống Kê Độ Phủ & Đối Soát 13 Bảng CSDL Thực Tế](#3-thống-kê-độ-phủ--đối-soát-13-bảng-csdl-thực-tế)

---

### 1. NGUYÊN TẮC THIẾT LẬP MA TRẬN TRUY VẾT (TRACEABILITY DESIGN PRINCIPLES)

Ma trận truy vết đa tầng là công cụ kiểm toán kỹ thuật tối cao, liên kết chặt chẽ mọi mắt xích trong chu trình phát triển phần mềm X-SENTINEL V3:
$$\text{Feature Requirement (F-01..F-28)} \iff \text{Backend Service} \iff \text{API Endpoint (19 Paths / 21 Ops)} \iff \text{13 DB Tables} \iff \text{Page (P01..P10)} \iff \text{Component (C01..C35)}$$

Đảm bảo:
- **Không có tính năng "mồ côi" (Zero Orphan Features):** Toàn bộ 28 tính năng chuẩn mực từ `02-FEATURE-INVENTORY.md` đều có đầy đủ ánh xạ tới Backend Router, CSDL và giao diện.
- **Không có thực thể CSDL ảo (Zero Phantom Tables):** Toàn bộ các bảng CSDL ánh xạ trực tiếp vào 13 bảng SQLAlchemy thực tế (`users`, `roles`, `user_roles`, `model_versions`, `analysis_jobs`, `analysis_results`, `detector_scores`, `alerts`, `artifacts`, `audit_events`, `experiment_runs`, `jev_ai_runs`, `jev_ai_feedback`). Đã loại bỏ hoàn toàn 100% các bảng giả tưởng không tồn tại trong backend.
- **Không có giao diện "ảo" (Zero Ghost UI):** Không còn gọi các endpoint ảo không tồn tại (chuẩn hóa sang `/v1/ai/explain`, `/v1/ai/runs`, `/v1/ai/runs/{run_id}/feedback` và đánh dấu mock dữ liệu cho Benchmark P09).

---

### 2. BẢNG MA TRẬN TRUY VẾT ĐA TẦNG 28 TÍNH NĂNG CHUẨN MỰC F-01 ĐẾN F-28

#### PHÂN HỆ 1: INGESTION & CORE DETECTION (F-01 ĐẾN F-10)

| Mã ID | Tên Tính Năng Nghiệp Vụ | Dịch Vụ Backend | API Endpoint | Bảng CSDL Thực Tế | Trang UI | Thành Phần (Component) | Tác Vụ Frontend | Bộ Kiểm Thử (Test) |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **F-01** | Kiểm thực và Chuẩn hóa Vector EMBER | `schema.py` / `DetectorService` | `POST /v1/analyze/vector` | `analysis_jobs` | P01 (`/analyze`) | C21 (`FeatureVectorEditor`), C01 (`Button`), C02 (`Input`) | `TASK-FE-11`, `TASK-FE-12` | `test_be04_domain_schema_views.py`, `MSW-01` |
| **F-02** | Phân rã Ngữ nghĩa 3-View | `FeatureViewDecomposer` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}` | `analysis_results` (`view_contributions`) | P02 (`/analysis/{id}`) | C09 (`HeroVerdictCard`), C10 (`RadialConfidenceGauge`) | `TASK-FE-13`, `TASK-FE-14` | `test_views.py`, `Unit-Views` |
| **F-03** | Suy diễn Mô hình LightGBM & TreeSHAP | `LightGBMService`, `TreeSHAPService` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}` | `analysis_results` (`malware_score`), `model_versions` | P02 (`/analysis/{id}`), P03 (`/explainability`) | C16 (`ShapWaterfallChart`), C17 (`TopFeaturesBarChart`) | `TASK-FE-16` | `test_be05_lightgbm_shap_service.py` |
| **F-04** | Tín hiệu M1: TADR (Attribution Dominance) | `m1_tadr.py` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}` | `detector_scores` (`M1`) | P02 (`/analysis/{id}`) | C13 (`ModuleScoreRow`) | `TASK-FE-14` | `test_be06_m1_tadr.py` |
| **F-05** | Tín hiệu M2: Tabular STRIP (Perturbation) | `m2_strip.py` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}` | `detector_scores` (`M2`) | P02 (`/analysis/{id}`) | C13 (`ModuleScoreRow`) | `TASK-FE-14` | `test_be06_m2_strip.py` |
| **F-06** | Tín hiệu M3: View Concentration | `m3_view.py` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}` | `detector_scores` (`M3`) | P02 (`/analysis/{id}`) | C13 (`ModuleScoreRow`) | `TASK-FE-14` | `test_be06_m3_view.py` |
| **F-07** | Tín hiệu M4: Cross-View Disagreement | `m4_cross_view.py` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}` | `detector_scores` (`M4`) | P02 (`/analysis/{id}`) | C13 (`ModuleScoreRow`) | `TASK-FE-14` | `test_be06_m4_cross_view.py` |
| **F-08** | Tín hiệu M5: Semantic Plausibility Rules | `m5_semantic.py` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}` | `detector_scores` (`M5`) | P02 (`/analysis/{id}`) | C13 (`ModuleScoreRow`) | `TASK-FE-14` | `test_be06_m5_semantic.py` |
| **F-09** | Động cơ Tổng hợp Tín hiệu (Fusion Engine) | `FusionEngine` / `calibration.py` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}` | `analysis_results` (`suspicion_score`, `threshold`) | P02 (`/analysis/{id}`) | C10 (`RadialConfidenceGauge`), C13 (`ModuleScoreRow`) | `TASK-FE-14` | `test_be07_fusion_engine.py` |
| **F-10** | Chính sách Quyết định Phán quyết | `decision.py` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}` | `analysis_results` (`decision`), `alerts` | P02 (`/analysis/{id}`) | C09 (`HeroVerdictCard`), C15 (`StatusPill`) | `TASK-FE-13`, `TASK-FE-14` | `test_be07_decision_golden_cases.py` |

---

#### PHÂN HỆ 2: INGESTION & GATING NHỊ PHÂN PE (F-11 ĐẾN F-12)

| Mã ID | Tên Tính Năng Nghiệp Vụ | Dịch Vụ Backend | API Endpoint | Bảng CSDL Thực Tế | Trang UI | Thành Phần (Component) | Tác Vụ Frontend | Bộ Kiểm Thử (Test) |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **F-11** | Trích xuất Đặc trưng PE Tĩnh (Phase 2) | `raw_pe.py` (LIEF Parser) | *Offline CLI Static Parser* | *None* | P01 (`/analyze`) | C22 (`SamplePresetLoader`) | `TASK-FE-12` | `test_raw_pe_malformed.py` |
| **F-12** | Khóa An toàn Cổng Nạp Tệp PE (Raw PE Gate)| `Router Gating` | `POST /v1/analyze/file` (501 `XS_FEATURE_DISABLED`) | *None* | P01 (`/analyze`) | C06 (`Badge`), C08 (`Dialog`) | `TASK-FE-12` | `test_raw_pe_disabled.py` |

---

#### PHÂN HỆ 3: BẰNG CHỨNG PHÁP CHỨNG & KIỂM TOÁN BẤT BIẾN (F-13 ĐẾN F-15)

| Mã ID | Tên Tính Năng Nghiệp Vụ | Dịch Vụ Backend | API Endpoint | Bảng CSDL Thực Tế | Trang UI | Thành Phần (Component) | Tác Vụ Frontend | Bộ Kiểm Thử (Test) |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **F-13** | Sinh Bằng chứng Pháp chứng Canonical Evidence | `evidence.py` | `POST /v1/analyze/vector`, `GET /v1/analysis/{id}/evidence` | `analysis_results`, `artifacts` | P02 (`/analysis/{id}`) | C12 (`EvidenceHashBlock`), C14 (`JsonViewer`) | `TASK-FE-13` | `test_be08_canonical_evidence_contract.py` |
| **F-14** | Ghi Nhật ký Bất biến (Append-Only Audit Log) | `audit_event.py` | Internal / `POST /v1/analyze/vector` | `audit_events` | P02, P08 | C14 (`JsonViewer`), C30 (`DataTable`) | `TASK-FE-14` | `test_be08_audit_write_failure.py` |
| **F-15** | Tra cứu & Xác minh Tính toàn vẹn Bằng chứng | `evidence.py` | `GET /v1/analysis/{id}/evidence` | `analysis_results`, `artifacts` | P02 (`/analysis/{id}`) | C12 (`EvidenceHashBlock`) | `TASK-FE-13` | `test_be08_evidence_hashing_integrity.py` |

---

#### PHÂN HỆ 4: LỊCH SỬ PHÂN TÍCH & QUẢN LÝ TRUY CẬP (F-16 ĐẾN F-18)

| Mã ID | Tên Tính Năng Nghiệp Vụ | Dịch Vụ Backend | API Endpoint | Bảng CSDL Thực Tế | Trang UI | Thành Phần (Component) | Tác Vụ Frontend | Bộ Kiểm Thử (Test) |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **F-16** | Xem Danh sách Lịch sử Phân tích & Lọc | `HistoryService` | `GET /v1/analysis` | `analysis_jobs`, `analysis_results` | P05 (`/history`) | C30 (`DataTable`), C02 (`Input`), C07 (`Select`) | `TASK-FE-15` | `test_be09_core_api.py` |
| **F-17** | Xem Chi tiết Bản ghi Phân tích & Forensic Data | `AnalysisService` | `GET /v1/analysis/{id}` | `analysis_jobs`, `analysis_results`, `detector_scores`, `artifacts` | P02 (`/analysis/{id}`) | C09 (`HeroVerdictCard`), C10, C12, C13 | `TASK-FE-13`, `TASK-FE-14` | `test_be09_core_api.py` |
| **F-18** | Bảo vệ Quyền sở hữu Bản ghi (Chống BOLA/IDOR) | `auth.py` (`assert_job_ownership`) | `GET /v1/analysis/{id}`, `GET /v1/analysis/{id}/evidence`, `GET /v1/ai/runs/{run_id}` | `analysis_jobs` (`user_id`), `users` | P02, P03, P04 | C34 (`BOLAErrorView`), C08 (`Dialog`) | `TASK-FE-03`, `TASK-FE-13` | `test_be15_security_rbac_blind.py` |

---

#### PHÂN HỆ 5: QUẢN LÝ & TÁC CHIẾN CẢNH BÁO SOC (F-19 ĐẾN F-21)

| Mã ID | Tên Tính Năng Nghiệp Vụ | Dịch Vụ Backend | API Endpoint | Bảng CSDL Thực Tế | Trang UI | Thành Phần (Component) | Tác Vụ Frontend | Bộ Kiểm Thử (Test) |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **F-19** | Xem Danh sách Cảnh báo SOC & Lọc | `AlertService` | `GET /v1/alerts` | `alerts`, `analysis_jobs` | P06 (`/alerts`) | C11 (`MetricCard`), C30 (`DataTable`), C15 (`StatusPill`) | `TASK-FE-18` | `test_be09_core_api.py` |
| **F-20** | Xem Chi tiết Cảnh báo Đơn lẻ | `AlertService` | `GET /v1/alerts/{alert_id}` | `alerts`, `analysis_jobs`, `analysis_results` | P07 (`/alerts/{id}`) | C26 (`AlertStatusStepper`), C11 (`MetricCard`) | `TASK-FE-19` | `test_be09_core_api.py` |
| **F-21** | Cập nhật Vòng đời Trạng thái Cảnh báo | `AlertService` | `PATCH /v1/alerts/{alert_id}` | `alerts`, `audit_events` | P07 (`/alerts/{id}`) | C26 (`AlertStatusStepper`), C28 (`DangerousActionModal`) | `TASK-FE-20` | `test_be09_core_api.py` |

---

#### PHÂN HỆ 6: KHUYẾN NGHỊ CỐ VẤN AN NINH JEV AI (F-22 ĐẾN F-25)

| Mã ID | Tên Tính Năng Nghiệp Vụ | Dịch Vụ Backend | API Endpoint | Bảng CSDL Thực Tế | Trang UI | Thành Phần (Component) | Tác Vụ Frontend | Bộ Kiểm Thử (Test) |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **F-22** | Kiểm tra Trạng thái Runtime Jev AI | `JevStatusService` | `GET /v1/ai/status` | *In-Memory LM Studio Probe* | P04 (`/ai-advisory`), P08 (`/system/status`) | C06 (`Badge`), C15 (`StatusPill`) | `TASK-FE-17` | `test_be03_foundation_health_readiness.py` |
| **F-23** | Thực thi Luồng Cố vấn AI (Explain/Triage/Compare/Report) | `JevAIService` | `POST /v1/ai/explain`, `GET /v1/ai/runs`, `GET /v1/ai/runs/{run_id}` | `jev_ai_runs` | P04 (`/ai-advisory`) | C25 (`JevAdvisoryContainer`), C23 (`MitreAttackMatrixTable`), C24 (`PlaybookStepList`) | `TASK-FE-17` | `test_be13_jev_persistence_api_feedback.py` |
| **F-24** | Thu thập và Xem Phản hồi Đánh giá AI | `JevAIService` | `POST /v1/ai/runs/{run_id}/feedback`, `GET /v1/ai/runs/{run_id}/feedback` | `jev_ai_feedback` | P04 (`/ai-advisory`) | C01 (`Button`), C02 (`Input`), C30 (`DataTable`) | `TASK-FE-17` | `test_be13_jev_persistence_api_feedback.py` |
| **F-25** | Hỏi đáp Tài liệu Hệ thống qua AI (Phase 2 Gated)| `Router Gating` | `POST /v1/ai/docs/ask` (501 `XS_FEATURE_DISABLED`) | *None* | P04 (Gated Phase 2) | C08 (`Dialog`) | `TASK-FE-17` | `test_be13_jev_persistence_api_feedback.py` |

---

#### PHÂN HỆ 7: GIÁM SÁT HẠ TẦNG, SỨC KHỎE & BENCHMARK (F-26 ĐẾN F-28)

| Mã ID | Tên Tính Năng Nghiệp Vụ | Dịch Vụ Backend | API Endpoint | Bảng CSDL Thực Tế | Trang UI | Thành Phần (Component) | Tác Vụ Frontend | Bộ Kiểm Thử (Test) |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **F-26** | Kiểm tra Sức khỏe và Độ sẵn sàng Hệ thống | `HealthService` | `GET /health`, `GET /ready` | *In-Memory DB Revision Check* | P08 (`/system/status`) | C15 (`StatusPill`), C06 (`Badge`) | `TASK-FE-21` | `test_be03_foundation_health_readiness.py` |
| **F-27** | Kiểm tra Trạng thái Cấu hình & Phiên bản CSDL | `ConfigService` | `GET /v1/config/status` | `model_versions`, `roles`, `users` | P08 (`/system/status`), P10 (`/auth/switch`) | C35 (`RoleProfileBadge`), C06 (`Badge`) | `TASK-FE-05`, `TASK-FE-21` | `test_be01_environment_config.py` |
| **F-28** | Giám sát Telemetry Phần cứng & Prometheus Metrics | `TelemetryService`, `PrometheusExporter` | `GET /v1/system/telemetry`, `GET /v1/system/metrics`, `GET /metrics` | *OS Hardware (`psutil`)* | P08 (`/system/status`) | C19 (`TelemetryGauge`), C14 (`JsonViewer`) | `TASK-FE-21` | `test_be17_benchmarks.py` |

---

### 3. THỐNG KÊ ĐỘ PHỦ & ĐỐI SOÁT 13 BẢNG CSDL THỰC TẾ

- **Tổng số tính năng chuẩn mực đối soát:** $28 / 28$ tính năng (`F-01` đến `F-28`) từ `02-FEATURE-INVENTORY.md` ($100\%$ hoàn bị).
  - 25 tính năng `IMPLEMENTED_VERIFIED`
  - 2 tính năng `DISABLED_BY_DESIGN` (`F-12` Raw PE 501, `F-25` Docs Ask 501)
  - 1 tính năng `IMPLEMENTED_UNTESTED` (`F-11` Static CLI LIEF parser)
  - 0 tính năng `BLOCKED_PENDING_INPUTS` (toàn bộ 28 tính năng nghiệp vụ đã được triển khai/khóa theo thiết kế)
- **Tổng số Endpoints API được ánh xạ:** 21 HTTP Operations trên 19 Unique Path Templates ($100\%$ bao phủ).
- **Tổng số Bảng CSDL Thực tế Được Ánh xạ (13/13 bảng SQLAlchemy):**
  1. `users` (F-18, F-27)
  2. `roles` (F-27)
  3. `user_roles` (F-27)
  4. `model_versions` (F-03, F-27)
  5. `analysis_jobs` (F-01, F-16, F-17, F-18, F-19, F-20)
  6. `analysis_results` (F-02, F-03, F-09, F-10, F-13, F-15, F-16, F-17, F-20)
  7. `detector_scores` (F-04, F-05, F-06, F-07, F-08, F-17)
  8. `alerts` (F-10, F-19, F-20, F-21)
  9. `artifacts` (F-13, F-15, F-17)
  10. `audit_events` (F-14, F-21)
  11. `experiment_runs` (Ánh xạ qua offline runner cho Benchmark P09)
  12. `jev_ai_runs` (F-23)
  13. `jev_ai_feedback` (F-24)
- **Các bảng giả tưởng đã loại bỏ hoàn toàn (6 bảng):** Đã loại bỏ 100% các thực thể không tồn tại trong CSDL SQLAlchemy 13 bảng thực tế.
- **Tổng số Trang giao diện Frontend:** $10 / 10$ trang P01–P10 ($100\%$ có đặc tả kỹ thuật).
- **Tổng số Thành phần giao diện tái sử dụng:** $35 / 35$ components C01–C35 ($100\%$ có TypeScript Props).
- **Tổng số Tác vụ triển khai Frontend:** $25 / 25$ tasks (`TASK-FE-01` đến `TASK-FE-25`).
