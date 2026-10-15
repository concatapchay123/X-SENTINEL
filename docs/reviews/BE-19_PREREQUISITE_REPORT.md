# BE-19 PREREQUISITE AUDIT & GATE DECISION REPORT
**X-SENTINEL V3 — Phase 2 Raw PE Ingestion & LIEF Static Extraction**
**Date:** 2026-10-13  
**Status:** PREREQUISITE NO-GO FOR PRODUCTION ACTIVATION / GO FOR STATIC ISOLATED IMPLEMENTATION

---

## 1. Executive Summary

Theo chỉ đạo tại **Master Implementation Prompt — PLAN-BE-19**, công đoạn kích hoạt tiếp nhận tệp thực thi Windows (Raw Portable Executable - PE) chỉ được phép tiến hành khi cả hai điều kiện tiên quyết (Critical Prerequisite Gates) được kiểm chứng độc lập:
1. **BE-04 PASS**: Đã xác minh thực nghiệm toàn diện trên 49 unit tests của `test_be04_domain_schema_views.py` và 4 schema/views tests (`test_schema.py`, `test_views.py`).
2. **Extractor / Schema Equivalence Gate PASS**: Kiểm tra đối sánh song song giữa bộ trích xuất chuẩn tham chiếu (Approved Reference Extractor) và bộ trích xuất ứng viên (Candidate Extractor) trên tập mẫu nhị phân đối sánh vàng (Golden Paired PE Corpus).

Kết quả rà soát thực nghiệm cho thấy:
- **BE-04**: **PASS** (100% tuân thủ cấu trúc 2.381 chiều, float hữu hạn, 3 semantic views, xác minh băm cấu hình phân rã demo `276be235...`).
- **Extractor Equivalence Gate**: **NO-GO FOR PRODUCTION RAW PE ACTIVATION**.
  - Môi trường thực thi hiện tại đang cài đặt `lief==1.0.0-d05b3499b` và `numpy==2.5.0`.
  - Gói chuẩn EMBER 2018 (`ember.features.PEFeatureExtractor`) phụ thuộc cứng vào `lief==0.9.0` và NumPy 1.x. Khi gọi `raw_features(bytez)` trên tệp thực thi PE, thư viện sụp đổ với lỗi:
    - `AttributeError: module 'lief' has no attribute 'bad_format'` (do LIEF 1.0 tái cấu trúc toàn bộ cây ngoại lệ sang enum `lief.lief_errors`).
    - `AttributeError: module 'numpy' has no attribute 'int'` trong `ByteEntropyHistogram` (do NumPy 2.0 bãi bỏ bí danh `np.int`).
    - LIEF 1.0 đổi tên Data Directory 6 từ `DEBUG` thành `DEBUG_DIR`.
  - Repository hiện tại **không chứa bất kỳ tệp thực thi PE nhị phân nào** (`.exe` / `.dll` = 0 tệp tin). Bộ dữ liệu EMBER 2018 chính thức từ Endgame/Elastic chỉ phân phối các tệp đặc trưng trích xuất sẵn dạng JSON (`test_features.jsonl`) và ma trận mmap (`X_test.dat`), không phát hành tệp nhị phân gốc.

**Quyết định Cổng (Prerequisite Decision):**
- **PREREQUISITE NO-GO**: Giữ nguyên trạng thái vô hiệu hóa đóng an toàn (fail-closed) của Raw PE trong API sản xuất (`POST /v1/analyze/file` trả về HTTP 501 `XS_FEATURE_DISABLED`).
- Không kết nối parser vào luồng suy luận Detector chính để bảo vệ tính toàn vẹn khoa học.
- Triển khai toàn diện bộ adapter tĩnh an toàn `RawPEFeatureExtractor` trong `backend/src/x_sentinel/data/raw_pe.py` với cờ mặc định `enabled=False` (kích hoạt ngoại lệ `FeatureGatedError` kế thừa `NotImplementedError` để giữ vững hợp đồng kiểm thử an ninh).
- Hoàn thiện đầy đủ các bộ kiểm thử tự động cho cả 3 tiêu chí nghiệm thu: No-Execution (5 tests), Malformed PE (29 tests), Feature Equivalence & Gate Audit (11 tests).

---

## 2. Ma trận Xác minh Điều kiện Tiên quyết (Prerequisite Verification Matrix)

| Cổng Kiểm Tra | Yêu Cầu Bắt Buộc | Bằng Chứng Thực Nghiệm Đo Đạc | Kết Luận |
|---|---|---|---|
| **BE-04 Schema & Views** | PASS | 49 tests tại `test_be04_domain_schema_views.py`, 3 tests tại `test_schema.py`, 1 test tại `test_views.py` đều đạt 100%. Vector 2.381 chiều, float hữu hạn, kiểm soát bounds chặt chẽ. | **PASS** |
| **Approved Reference Extractor** | Phiên bản EMBER 2018 chính thức | Gói `ember` trong môi trường cài đặt gặp lỗi không tương thích với LIEF 1.0 và NumPy 2.5 khi phân tích raw PE. | **BLOCKED (LIEF/NumPy version drift)** |
| **LIEF Dependency Version** | LIEF 0.9.0 tương thích EMBER 2018 | Môi trường cài đặt `lief==1.0.0-d05b3499b` (cảnh báo từ `ember`: *EMBER feature version 2 were computed using lief 0.9.0-*). | **BLOCKED** |
| **Golden PE Binary Corpus** | Tập mẫu PE nhị phân đối sánh vàng | Tìm kiếm toàn bộ repo: 0 tệp `.exe`, 0 tệp `.dll`. EMBER2018 chỉ phân phối vector/JSONL. | **BLOCKED (Thiếu corpus PE gốc)** |
| **Paired Reference Vectors** | Cặp vector tham chiếu tương ứng PE | Vector JSONL có sẵn (`test_features.jsonl` dòng 0 khớp 100% `X_test.dat` dòng 0), nhưng không có cặp tệp nhị phân gốc. | **PARTIAL** |
| **Kích hoạt Raw PE Sản xuất** | Chỉ sau khi Equivalence Gate PASS | API `/v1/analyze/file` duy trì HTTP 501 `XS_FEATURE_DISABLED`; adapter `RawPEFeatureExtractor` duy trì fail-closed `enabled=False`. | **FAIL-CLOSED PRESERVED** |

---

## 3. Danh mục Rủi ro & Khuyến nghị Khắc phục

1. **Rủi ro Trôi dạt Thư viện (Dependency Drift)**:
   - Thư viện `lief` từ 0.9.0 lên 1.0.0 có nhiều thay đổi breaking trong API đối tượng C++ bindings (nanobind thay pybind11, tái cấu trúc enum lỗi, đổi tên trường dữ liệu).
   - *Khắc phục*: Ứng viên `raw_pe.py` đã chuẩn hóa các khác biệt này bằng cách bao bọc các hàm trích xuất tương thích (bản đồ Data Directory ánh xạ `DEBUG_DIR` -> `DEBUG`, kiểm tra mảng an toàn, chuẩn hóa kiểu dữ liệu NumPy 2.x).
2. **Thiếu Tập Mẫu PE Nhị Phân Đối Sánh Vàng**:
   - Để chính thức phê duyệt Equivalence Gate, cần xây dựng một harness kiểm thử có tối thiểu 100 mẫu PE an toàn (synthetic compiler builds hoặc benign system files được cấp phép) kèm theo vector tham chiếu được trích xuất bằng môi trường chuẩn LIEF 0.9.0 / Python 3.7.
