# BE-19 FEATURE EQUIVALENCE & EXTRACTOR AUDIT REPORT
**X-SENTINEL V3 — EMBER2018 Group Breakdown, Numerical Tolerance & Prerequisite Audit**
**Date:** 2026-10-13  
**Status:** CANONICAL SCHEMA VALIDATED (2,381 DIMS) / DIVERGENCE AUDIT DOCUMENTED

---

## 1. Mục tiêu Kiểm thử Tương đương Đặc trưng (Feature Equivalence)

Theo Master Implementation Prompt PLAN-BE-19, tiêu chí **Feature Equivalence** không chỉ đo đếm số chiều (2.381), mà đòi hỏi phải kiểm chứng:
1. Phân chia chính xác từng nhóm đặc trưng theo tài liệu chuẩn EMBER 2018.
2. Thuật toán băm và sắp xếp thứ tự các chiều băm (FeatureHasher).
3. Miền giá trị số (float hữu hạn, chuẩn hóa tần suất byte và entropy).
4. Tính đơn định (determinism) khi trích xuất lặp lại trên cùng một mẫu PE.
5. Khả năng tương thích phân cắt 3 Semantic Views (Structural, Behavioral, Metadata).
6. Khảo sát thực nghiệm đối sánh với bộ dữ liệu EMBER 2018 chính thức (`test_features.jsonl` và `X_test.dat`).

---

## 2. Bảng Phân rã Nhóm Đặc trưng Chuẩn (Feature Group Breakdown)

| Nhóm Đặc Trưng (Feature Group) | Số Chiều Chuẩn | Mô Tả Kỹ Thuật | Phương Thức Trích Xuất | Kết Quả Đo Thực Tế |
|---|---|---|---|---|
| **ByteHistogram** | 256 | Phân phối tần suất 256 giá trị byte (0x00 - 0xFF) chuẩn hóa tổng = 1.0 | Phân tích mảng byte tĩnh (NumPy) | **256** (khớp 100%) |
| **ByteEntropyHistogram** | 256 | Lưới 16 x 16 (16 khoảng entropy x 16 khoảng giá trị byte coarse `block >> 4`) trên cửa sổ trượt 2048 bytes, bước nhảy 1024 bytes (chuẩn Saxe & Berlin 2015 trong EMBER2018) | Phân tích mảng byte tĩnh (NumPy 2.x) | **256** (khớp 100%) |
| **StringExtractor** | 104 | Thống kê chuỗi in được >= 5 ký tự: số lượng (1), độ dài trung bình (1), tổng ký tự in được (1), phân phối 96 ký tự in được (96), entropy chuỗi (1); cùng số lần xuất hiện trong luồng byte thô của đường dẫn `c:\\` (1), URL `https?://` (1), khóa Registry `HKEY_` (1), chữ ký 'MZ' (1) | Biểu thức chính quy Regex trên byte stream | **104** (khớp 100%) |
| **GeneralFileInfo** | 10 | Kích thước tệp, kích thước ảo (vsize), cờ debug, số lượng hàm export, số lượng hàm import, cờ relocations, cờ resources, cờ chữ ký số, cờ TLS, số lượng symbols | Static PE parser (LIEF / PE headers) | **10** (khớp 100%) |
| **HeaderFileInfo** | 62 | Timestamp COFF (1), băm Machine (10), băm Characteristics (10), băm Subsystem (10), băm DLL Characteristics (10), băm Magic (10), cùng 11 trường số nguyên phiên bản và kích thước | Static COFF & Optional Header parser | **62** (khớp 100%) |
| **SectionInfo** | 255 | Tổng số section (1), số section kích thước 0 (1), số section tên rỗng (1), số section RX (1), số section W (1), băm kích thước section (50), băm entropy section (50), băm vsize section (50), băm tên entry section (50), băm đặc tính section (50) | Static Section Table parser | **255** (khớp 100%) |
| **ImportsInfo** | 1280 | Băm tên thư viện liên kết động (256), băm hàm nhập khẩu kèm tên thư viện dạng `dll:function` (1024) qua scikit-learn FeatureHasher | Static Import Table parser | **1280** (khớp 100%) |
| **ExportsInfo** | 128 | Băm danh sách tên hàm xuất khẩu qua FeatureHasher (128) | Static Export Table parser | **128** (khớp 100%) |
| **DataDirectories** | 30 | Cặp `(kích thước, RVA)` cho 15 thư mục dữ liệu chuẩn theo thứ tự chỉ mục Microsoft PE (0..14) | Static Data Directory Table parser | **30** (khớp 100%) |
| **TỔNG CỘNG** | **2381** | **Khớp chính xác 100% với Canonical Vector Schema của X-SENTINEL V3** | **Toàn bộ pipeline tĩnh** | **2381 / 2381 PASS** |

---

## 3. Kết quả Thực nghiệm Đối sánh Thực tế

### 3.1. Tính Đơn Định (Determinism)
- Trích xuất lặp lại 2 lần liên tiếp trên cùng một mẫu PE nhị phân:
  - Vector 1 vs Vector 2:
  - Sai số tuyệt đối tối đa: **0.00000000** (bit-exact).
  - Không tồn tại trạng thái ngẫu nhiên hay phụ thuộc thứ tự xử lý.

### 3.2. Tính Hợp Lệ Theo Schema & Phân Cắt 3 Semantic Views
- Vector trích xuất được đưa qua `validate_vector()` trong `x_sentinel.data.schema`:
  - 100% phần tử là float hữu hạn (không NaN, không Inf).
  - Thỏa mãn toàn bộ ràng buộc kiểu dữ liệu.
- Vector được đưa qua `load_view_map(Path("configs/views.demo.yaml")).split()`:
  - Nhánh `structural`: 461 chiều.
  - Nhánh `behavioral`: 1.342 chiều.
  - Nhánh `metadata`: 578 chiều.
  - Tổng số chiều phân rã: đúng **2.381 chiều**, không bỏ sót và không trùng lặp.

### 3.3. Đối sánh Vector hóa Chuẩn trên Tập Dữ liệu EMBER 2018 Thực tế
- Sử dụng bản ghi JSON đầu tiên trong tệp `datasets/ember2018/test_features.jsonl` (SHA-256: `163ced46c18ef09d8e2f0ee4b16decf74a533f22ba3b599c72a6730435f32cc9`).
- Thực hiện vector hóa bằng `ember.PEFeatureExtractor(2).process_raw_features()`.
- So sánh từng phần tử với hàng 0 của ma trận nhị phân chuẩn `datasets/ember2018/X_test.dat`.
- **Kết quả đo đạc**:
  - `Max Absolute Difference = 0.0`.
  - Khớp bit-exact 100% với ground truth benchmark của Elastic/Endgame.

### 3.4. Đối sánh Đa Bản ghi & Đơn vị Trích xuất Độc lập
- Kiểm nghiệm toàn bộ 9 nhóm đặc trưng trên 10 bản ghi liên tiếp của `test_features.jsonl`:
  - Sai số tuyệt đối tối đa so với `ember.PEFeatureExtractor(2).process_raw_features`: **0.00000000** trên toàn bộ 23.810 điểm dữ liệu đối sánh.
- Kiểm nghiệm đơn vị `StringExtractor`:
  - So sánh trực tiếp giữa `extract_strings()` và `ember.features.StringExtractor()` trên chuỗi byte kiểm thử đa dạng: **Max Absolute Difference = 0.0**.
- Kiểm nghiệm ngữ nghĩa băm khi nhị phân rỗng (`binary=None`):
  - Khớp 100% giá trị băm chuỗi vô hướng `""` (băm ra 1.0) của EMBER `HeaderFileInfo` và `SectionInfo`.

---

## 4. Báo cáo Chi tiết Bất đồng Phiên bản LIEF & NumPy (Drift Audit)

Kiểm thử `test_audit_legacy_ember_lief_version_incompatibility` tại `backend/tests/test_raw_pe_equivalence.py` đã chỉ ra nguồn gốc kỹ thuật ngăn cản việc kích hoạt Raw PE sản xuất:
1. **Lỗi `lief.bad_format`**:
   Trong `ember/features.py` dòng 537, mã nguồn legacy giả định `lief.bad_format` là một ngoại lệ Python có sẵn trên module `lief`. Trên `lief==1.0.0`, toàn bộ cơ chế báo lỗi chuyển thành enum `lief.lief_errors`, dẫn đến `AttributeError`.
2. **Lỗi `np.int`**:
   Trong `ember/features.py` dòng 100, mã nguồn khởi tạo `np.zeros((16, 16), dtype=np.int)`. Trên NumPy 2.x, bí danh này đã bị loại bỏ hoàn toàn, gây sụp đổ mã nguồn.
3. **Đổi tên Data Directory `DEBUG`**:
   Trên LIEF 1.0, thư mục debug được định danh là `DEBUG_DIR`. Nếu parser so sánh chuỗi trực tiếp mà không ánh xạ về `DEBUG`, 2 đặc tính kích thước và RVA của thư mục này sẽ bị lệch.

*Bộ adapter ứng viên `RawPEFeatureExtractor` trong `raw_pe.py` đã xử lý triệt để các khác biệt này cho quá trình trích xuất tĩnh, nhưng việc kích hoạt ở tầng sản xuất vẫn bị giữ lại theo đúng nguyên tắc cổng bảo mật Fail-Closed.*
