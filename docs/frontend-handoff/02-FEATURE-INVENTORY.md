# X-SENTINEL V3 — BẢNG KIỂM KÊ VÀ ĐẶC TẢ CHI TIẾT TOÀN BỘ CHỨC NĂNG HỆ THỐNG
## 02-FEATURE-INVENTORY.md — Complete Feature Inventory & Business Specifications

> **Mục tiêu:** Cung cấp tài liệu đặc tả nghiệp vụ hoàn chỉnh, chi tiết đến từng trường dữ liệu, quy tắc kiểm thực, điều kiện rẽ nhánh và bằng chứng mã nguồn cho toàn bộ 28 chức năng thuộc 7 phân hệ của X-SENTINEL V3.  
> **Tiêu chuẩn:** Đáp ứng đầy đủ 9 tiêu chí bắt buộc (A đến I) cho từng chức năng.

---

## BẢNG TỔNG QUAN DANH MỤC TÍNH NĂNG (MASTER FEATURE MATRIX)

| Mã ID | Tên chức năng | Phân hệ (Domain) | Trạng thái triển khai | Quyền hạn (Roles) | Mức ưu tiên |
|---|---|---|---|---|:---:|
| **F-01** | Kiểm thực và Chuẩn hóa Vector EMBER | Ingestion & Core | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-02** | Phân rã Ngữ nghĩa 3-View | Detection Core | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-03** | Suy diễn Mô hình LightGBM & TreeSHAP | Model Service | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-04** | Tín hiệu M1: TADR (Thống trị Thuộc tính) | Detection Core | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-05** | Tín hiệu M2: Tabular STRIP (Entropy Pha trộn) | Detection Core | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-06** | Tín hiệu M3: View Concentration (Tập trung View)| Detection Core | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-07** | Tín hiệu M4: Cross-View Disagreement | Detection Core | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-08** | Tín hiệu M5: Semantic Plausibility Rules | Detection Core | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-09** | Động cơ Tổng hợp Tín hiệu (Fusion Engine) | Fusion Core | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-10** | Chính sách Quyết định Phán quyết (Decision Policy)| Fusion Core | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-11** | Trích xuất Đặc trưng PE Tĩnh (Phase 2) | Data / Raw PE | `IMPLEMENTED_UNTESTED` | Admin | P2 (Future) |
| **F-12** | Khóa An toàn Cổng Nạp Tệp PE (Raw PE Gate) | Security / API | `DISABLED_BY_DESIGN` | Tất cả (Trả về 501) | P0 (Critical) |
| **F-13** | Sinh Bằng chứng Pháp chứng Canonical Evidence | Audit & Integrity | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-14** | Ghi Nhật ký Bất biến (Append-Only Audit Log) | Audit & Integrity | `IMPLEMENTED_VERIFIED` | System / Internal | P0 (Critical) |
| **F-15** | Tra cứu và Xác minh Tính toàn vẹn Bằng chứng | Audit & Evidence | `IMPLEMENTED_VERIFIED` | Analyst, Evaluator, Admin | P1 (High) |
| **F-16** | Xem Danh sách Lịch sử Phân tích & Lọc đa tiêu chí | History Management| `IMPLEMENTED_VERIFIED` | Operator, Analyst, Evaluator, Admin | P0 (Critical) |
| **F-17** | Xem Chi tiết Bản ghi Phân tích & Forensic Data | History Management| `IMPLEMENTED_VERIFIED` | Operator, Analyst, Evaluator, Admin | P0 (Critical) |
| **F-18** | Bảo vệ Quyền sở hữu Bản ghi (Chống BOLA/IDOR) | Security / Auth | `IMPLEMENTED_VERIFIED` | Tất cả | P0 (Critical) |
| **F-19** | Xem Danh sách Cảnh báo SOC & Lọc | Alert Management | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P0 (Critical) |
| **F-20** | Xem Chi tiết Cảnh báo Đơn lẻ | Alert Management | `IMPLEMENTED_VERIFIED` | Operator, Analyst, Admin | P1 (High) |
| **F-21** | Cập nhật Vòng đời Trạng thái Cảnh báo | Alert Management | `IMPLEMENTED_VERIFIED` | Analyst, Admin | P0 (Critical) |
| **F-22** | Kiểm tra Trạng thái Runtime Jev AI | Jev AI Advisory | `IMPLEMENTED_VERIFIED` | Tất cả | P1 (High) |
| **F-23** | Thực thi Luồng Cố vấn AI (Explain/Triage/Compare/Report) | Jev AI Advisory | `IMPLEMENTED_VERIFIED` | Analyst, Admin | P0 (Critical) |
| **F-24** | Thu thập và Xem Phản hồi Đánh giá AI | Jev AI Advisory | `IMPLEMENTED_VERIFIED` | Analyst, Admin | P1 (High) |
| **F-25** | Hỏi đáp Tài liệu Hệ thống qua AI (Phase 2 Gated)| Jev AI Advisory | `DISABLED_BY_DESIGN` | Analyst, Admin (501) | P2 (Future) |
| **F-26** | Kiểm tra Sức khỏe và Độ sẵn sàng Hệ thống | System Observability | `IMPLEMENTED_VERIFIED` | Public / Tất cả | P0 (Critical) |
| **F-27** | Kiểm tra Trạng thái Cấu hình & Phiên bản CSDL | System Observability | `IMPLEMENTED_VERIFIED` | Public / Tất cả | P1 (High) |
| **F-28** | Giám sát Telemetry Phần cứng & Prometheus Metrics | System Observability | `IMPLEMENTED_VERIFIED` | Operator, Admin | P1 (High) |

---

## ĐẶC TẢ CHI TIẾT TỪNG CHỨC NĂNG (DETAILED SPECIFICATIONS)

---

### PHÂN HỆ 1: INGESTION & CORE DETECTION (F-01 ĐẾN F-10)

#### F-01: Kiểm thực và Chuẩn hóa Vector EMBER (Vector Input Validation)
- **A. Định danh:** `F-01` | Ingestion & Core | Đảm bảo tính toàn vẹn toán học của vector đầu vào trước khi chuyển giao cho mô hình học máy | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Operator, Analyst, Admin có quyền `analysis:submit`.
- **C. Điều kiện thực hiện:** Header chứa Bearer Token hợp lệ (hoặc chế độ dev auth=none). Concurrency limiter cho phép tiếp nhận (<50 requests đồng thời).
- **D. Input:**
  - `features` (`list[float]`, bắt buộc): Mảng chính xác 2.381 phần tử số thực.
  - `source_name` (`str`, tùy chọn): Nhãn định danh nguồn tệp hoặc mã mẫu (tối đa 255 ký tự).
  - `request_id` (`str`, tùy chọn): Chuỗi UUIDv4 định danh yêu cầu cho tính đơn định/idempotency.
  - *Validation Rules:* Không được chứa giá trị `NaN`, `+Infinity`, `-Infinity`. Số chiều khác 2.381 sẽ bị từ chối ngay lập tức.
- **E. Xử lý nghiệp vụ:**
  1. Kiểm tra kích thước mảng: Nếu `len(features) != 2381` -> Ném `VectorValidationError`.
  2. Duyệt từng phần tử ép kiểu `float(x)` và kiểm tra `math.isfinite(x)`. Nếu không hợp lệ -> Ném `VectorValidationError`.
  3. Chuẩn hóa làm tròn 6 chữ số thập phân phục vụ tính mã băm đầu vào `input_id`.
- **F. Output:** Vector chuẩn hóa `list[float]` sẵn sàng cho bộ nhớ đệm suy diễn.
- **G. Ngoại lệ:**
  - `HTTP 422 Unprocessable Entity` (`XS_INPUT_INVALID`): Số chiều khác 2.381 hoặc chứa giá trị không hữu hạn.
  - `HTTP 429 Too Many Requests` (`XS_DETECTOR_OVERLOADED`): Hệ thống quá tải >50 requests đồng thời.
- **H. Frontend implications:** Cần form nhập vector với 2 chế độ: (1) Tải tệp JSON chứa mảng số; (2) Dán văn bản thô. Cần bộ kiểm tra Client-side (Zod) đếm số lượng phần tử trước khi gửi nhằm tránh lãng phí băng thông mạng.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/data/schema.py:L15-L68`, `backend/tests/test_be04_domain_schema_views.py:L25-L89`.

---

#### F-02: Phân rã Ngữ nghĩa 3-View (3-View Semantic Decomposition)
- **A. Định danh:** `F-02` | Detection Core | Phân chia 2.381 đặc trưng thành 3 góc nhìn cấu trúc, hành vi và siêu dữ liệu | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Được gọi tự động trong pipeline phân tích.
- **C. Điều kiện thực hiện:** Vector đầu vào đã vượt qua kiểm tra `F-01`. Tệp ánh xạ `configs/views.demo.yaml` tồn tại và khớp mã băm `276be235...`.
- **D. Input:** Vector 2.381 chiều sạch từ `F-01`.
- **E. Xử lý nghiệp vụ:**
  1. Ánh xạ các chỉ mục đặc trưng theo cấu hình View Map:
     - **Structural View (461 chiều):** Header PE, bảng Section, đặc tính cờ máy.
     - **Behavioral View (1.342 chiều):** Danh sách thư viện nhập khẩu (256 chiều băm) và hàm API `dll:function` (1.024 chiều băm), hàm xuất khẩu (128 chiều băm).
     - **Metadata View (578 chiều):** Byte Histogram (256 chiều), Byte Entropy (256 chiều), Strings thống kê (104 chiều).
  2. Trích xuất thành 3 vector con độc lập không giao thoa và không thất thoát bất kỳ chiều nào (Tổng đúng 2.381).
- **F. Output:** Đối tượng `dict[str, list[float]]` chứa 3 khóa `structural`, `behavioral`, `metadata`.
- **G. Ngoại lệ:** `RuntimeError` (`XS_CONFIG_UNRESOLVED`) nếu tệp View Map bị sửa đổi trái phép làm lệch số chiều.
- **H. Frontend implications:** Không cần form nhập riêng. Cần hiển thị biểu đồ phân bố 3-View trên giao diện kết quả.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/data/views.py:L20-L95`, `backend/tests/test_views.py`.

---

#### F-03: Suy diễn Mô hình LightGBM & Bóc tách TreeSHAP (Model & SHAP Service)
- **A. Định danh:** `F-03` | Model Service | Tính toán xác suất mã độc tổng thể và phân bổ giá trị đóng góp Shapley cục bộ | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Kích hoạt tự động khi phân tích mẫu.
- **C. Điều kiện thực hiện:** Tệp mô hình `models/ember_model_2018.txt` có mã băm SHA-256 `509de4a8...`.
- **D. Input:** Vector 2.381 chiều sạch.
- **E. Xử lý nghiệp vụ:**
  1. Gọi `booster.predict(vector)` -> Trả về `malware_score` $\in [0.0, 1.0]$.
  2. Khởi tạo `TreeExplainer` trên 1.000 cây quyết định LightGBM.
  3. Tính toán chính xác vector SHAP values (2.381 số thực) phản ánh mức độ đóng góp (âm hoặc dương) của từng đặc trưng vào điểm số.
  4. Xác minh sai số thặng dư tổng SHAP so với output mô hình $< 10^{-10}$.
- **F. Output:** Cặp `(malware_score: float, shap_values: list[float])`.
- **G. Ngoại lệ:** Lỗi bộ nhớ hoặc lỗi thư viện native C++ LightGBM ném `RuntimeError`.
- **H. Frontend implications:** Hiển thị thẻ chỉ số `Malware Score` (0.00% – 100.00%) kèm thang đo màu (Xanh nếu < 0.50, Cam nếu 0.50-0.85, Đỏ nếu >= 0.85). Cung cấp bảng/biểu đồ Top 10 đặc trưng SHAP có ảnh hưởng lớn nhất.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/model/lightgbm_service.py:L30-L125`, `backend/src/x_sentinel/model/shap_service.py:L15-L65`.

---

#### F-04: Tín hiệu M1: TADR — Attribution Dominance Ratio (Detector M1)
- **A. Định danh:** `F-04` | Detection Core | Phát hiện mẫu backdoor dựa trên sự tập trung bất thường của thuộc tính SHAP vào một số ít đặc trưng trigger | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Thành phần tính toán tự động trong pipeline.
- **C. Điều kiện thực hiện:** Đã có vector SHAP từ `F-03`.
- **D. Input:** Vector SHAP 2.381 phần tử.
- **E. Xử lý nghiệp vụ:**
  1. Lấy trị tuyệt đối của toàn bộ giá trị SHAP: $|s_i|$.
  2. Sắp xếp giảm dần và tính tỷ lệ tổng giá trị của Top-$K$ đặc trưng ($K=10$) trên tổng giá trị của toàn bộ 2.381 đặc trưng:
     $$M_1 = \frac{\sum_{i=1}^{K} |s_{(i)}|}{\sum_{j=1}^{N} |s_j| + \epsilon}$$
  3. Chuẩn hóa điểm số về khoảng $[0.0, 1.0]$. Điểm càng cao biểu thị sự thống trị bất thường của một cụm trigger nhỏ.
- **F. Output:** `SignalResult(name="m1", score=float, diagnostics={"top_k_mass": float, "top_indices": list[int]})`.
- **G. Ngoại lệ:** Nếu không có vector SHAP, gán `score=0.0` kèm trạng thái `SKIPPED_NO_SHAP`.
- **H. Frontend implications:** Thẻ hiển thị tín hiệu M1 trong cụm "Detector Signals (M1–M5)" kèm tooltip giải thích nguyên lý toán học.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/detection/m1_tadr.py:L15-L65`.

---

#### F-05: Tín hiệu M2: Tabular STRIP (Shannon Entropy Perturbation)
- **A. Định danh:** `F-05` | Detection Core | Phát hiện backdoor bằng cách gây nhiễu pha trộn mẫu kiểm tra với tập mẫu lành tính cơ sở | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Thành phần tính toán tự động trong pipeline.
- **C. Điều kiện thực hiện:** Mô hình LightGBM sẵn sàng; bộ mẫu lành tính cơ sở (`benign_pool`, 32 mẫu) được nạp.
- **D. Input:** Vector 2.381 chiều và mô hình LightGBM.
- **E. Xử lý nghiệp vụ:**
  1. Lấy mẫu $N_{pert}=16$ mẫu lành tính từ pool cơ sở.
  2. Thực hiện pha trộn lồi (convex blending) giữa vector kiểm tra $x$ và mẫu lành tính $b_k$:
     $$\tilde{x}_k = \alpha \cdot x + (1 - \alpha) \cdot b_k, \quad \alpha = 0.5$$
  3. Cho từng mẫu nhiễu qua mô hình để lấy xác suất dự đoán $p_k$.
  4. Tính độ hỗn loạn entropy Shannon trung bình:
     $$H = -\frac{1}{N_{pert}} \sum_{k=1}^{N_{pert}} \left[ p_k \log_2 p_k + (1-p_k) \log_2(1-p_k) \right]$$
  5. Đối với mẫu chứa trigger backdoor độc hại, nhãn dự đoán bị khóa cứng dẫn đến entropy $H \to 0$. Điểm số M2 tính bằng $1.0 - \text{normalized}(H)$.
- **F. Output:** `SignalResult(name="m2", score=float, diagnostics={"mean_entropy": float, "perturbations": 16})`.
- **G. Ngoại lệ:** Nếu thiếu mô hình, trả về `score=0.0` với cờ `SKIPPED_NO_MODEL`.
- **H. Frontend implications:** Hiển thị điểm số M2, biểu đồ thanh trực quan hóa entropy thấp (cảnh báo nguy cơ trigger khóa nhãn).
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/detection/m2_strip.py:L20-L115`.

---

#### F-06: Tín hiệu M3: View Concentration (Mức độ Tập trung Góc nhìn)
- **A. Định danh:** `F-06` | Detection Core | Đo lường mức độ mất cân bằng đóng góp SHAP giữa 3 góc nhìn cấu trúc, hành vi và siêu dữ liệu | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Thành phần tính toán tự động trong pipeline.
- **C. Điều kiện thực hiện:** Đã phân rã vector SHAP thành 3 views theo `F-02`.
- **D. Input:** Phân đoạn SHAP theo 3 views.
- **E. Xử lý nghiệp vụ:**
  1. Tính tổng giá trị tuyệt đối SHAP trong từng view: $C_v = \sum_{j \in View_v} |s_j|$.
  2. Chuẩn hóa thành tỷ trọng đóng góp tương đối: $w_v = C_v / \sum C_k$.
  3. Tính hệ số bất bình đẳng tập trung (Max Ratio hoặc Gini Index giữa 3 giá trị $w_{structural}, w_{behavioral}, w_{metadata}$).
  4. Nếu toàn bộ đóng góp dồn bất thường vào 1 view duy nhất (ví dụ trigger chèn vào bảng export hoặc byte histogram), $M_3 \to 1.0$.
- **F. Output:** `SignalResult(name="m3", score=float, diagnostics={"contributions": {"structural": float, "behavioral": float, "metadata": float}})`.
- **G. Ngoại lệ:** Trả về `score=0.0` nếu thiếu SHAP hoặc View Map.
- **H. Frontend implications:** Biểu đồ hình quạt (Donut Chart) hoặc 3 thanh phần trăm thể hiện tỷ trọng đóng góp của 3 view.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/detection/m3_view.py:L15-L85`.

---

#### F-07: Tín hiệu M4: Cross-View Disagreement (Bất đồng thuận Đa góc nhìn)
- **A. Định danh:** `F-07` | Detection Core | Đo lường sự mâu thuẫn giữa phán đoán toàn thể và phán đoán cục bộ từng view đơn lẻ | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Thành phần tính toán tự động trong pipeline.
- **C. Điều kiện thực hiện:** Đã tính toán xong đóng góp 3 view từ `F-06` và điểm mô hình toàn thể từ `F-03`.
- **D. Input:** Điểm `malware_score` toàn thể và tỷ trọng đóng góp từng view.
- **E. Xử lý nghiệp vụ:**
  1. So sánh sự chênh lệch lớn nhất giữa các góc nhìn đối kháng (ví dụ View Hành vi kết luận sạch nhưng View Cấu trúc chỉ ra mã độc cao).
  2. Tính độ lệch phân kỳ Jensen-Shannon hoặc giá trị tuyệt đối hiệu số lớn nhất giữa các views.
  3. Chuẩn hóa điểm số $M_4 \in [0.0, 1.0]$. Điểm số cao chỉ ra sự mất đồng bộ đặc trưng của kỹ thuật né tránh qua backdoor.
- **F. Output:** `SignalResult(name="m4", score=float, diagnostics={"max_discrepancy": float, "conflicting_views": list[str]})`.
- **G. Ngoại lệ:** Trả về `score=0.0` nếu thiếu dữ liệu đầu vào.
- **H. Frontend implications:** Thẻ cảnh báo phân kỳ đa góc nhìn (Cross-View Conflict Indicator) giúp chuyên viên nhận diện ngay view nào đang che giấu trigger.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/detection/m4_cross_view.py:L15-L95`.

---

#### F-08: Tín hiệu M5: Semantic Plausibility Rules (Quy tắc Ngữ nghĩa Nhị phân)
- **A. Định danh:** `F-08` | Detection Core | Kiểm tra các vi phạm quy tắc logic thực tế của định dạng PE chỉ xuất hiện khi kẻ tấn công thao túng vector nhân tạo | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Thành phần tính toán tự động trong pipeline.
- **C. Điều kiện thực hiện:** Vector 2.381 chiều sạch từ `F-01`.
- **D. Input:** Vector đặc trưng.
- **E. Xử lý nghiệp vụ:**
  1. Quét qua tập quy tắc bất khả thi về mặt vật lý (Physical & Semantic Impossibility Rules):
     - Ví dụ: Số lượng hàm import bằng 0 nhưng kích thước file > 5MB.
     - Byte entropy = 0.0 trên section có cờ thực thi (RX).
     - Mâu thuẫn giữa tổng kích thước sections và Virtual Size.
  2. Mỗi vi phạm cộng dồn điểm phạt theo trọng số đã định trước trong `configs/m5_rules.json`.
  3. Chuẩn hóa điểm số $M_5 \in [0.0, 1.0]$.
- **F. Output:** `SignalResult(name="m5", score=float, diagnostics={"violations_count": int, "violated_rules": list[str]})`.
- **G. Ngoại lệ:** Nếu tệp cấu hình quy tắc lỗi, rơi vào chế độ heuristic cơ bản.
- **H. Frontend implications:** Danh sách các quy tắc vi phạm (nếu có) được liệt kê chi tiết dưới dạng checklist cảnh báo màu đỏ/cam.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/detection/m5_semantic.py:L15-L110`.

---

#### F-09: Động cơ Tổng hợp Tín hiệu (Fusion Engine)
- **A. Định danh:** `F-09` | Fusion Core | Tổng hợp 5 tín hiệu đơn lẻ M1–M5 thành điểm số nghi ngờ backdoor thống nhất (Fused Suspicion Score) | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Thành phần pipeline tự động.
- **C. Điều kiện thực hiện:** Đã có đầy đủ 5 giá trị tín hiệu $M_1, M_2, M_3, M_4, M_5 \in [0.0, 1.0]$.
- **D. Input:** Từ điển `signals: dict[str, float]` chứa đúng 5 khóa `m1` đến `m5`.
- **E. Xử lý nghiệp vụ:**
  1. Kiểm thực toàn bộ 5 giá trị float hữu hạn trong $[0.0, 1.0]$. Bất kỳ giá trị nào ngoài miền sẽ ném lỗi miền giá trị `SignalDomainError`.
  2. Áp dụng chiến lược tổng hợp đã cấu hình (Weighted Sum Convex Combination):
     $$\text{suspicion\_score} = \sum_{k=1}^{5} w_k \cdot M_k, \quad \sum w_k = 1.0$$
  3. Kẹp giá trị (clamping) trong phạm vi chặt $[0.0, 1.0]$.
- **F. Output:** Điểm số vô hướng `suspicion_score: float` và đối tượng `FusionResult`.
- **G. Ngoại lệ:**
  - `MissingSignalError`: Thiếu một trong các tín hiệu M1–M5.
  - `InvalidSignalError`: Tín hiệu không phải số thực hữu hạn.
  - `SignalDomainError`: Tín hiệu vi phạm miền $[0.0, 1.0]$.
- **H. Frontend implications:** Hiển thị thanh tiến trình điểm nghi ngờ (Suspicion Gauge) từ 0.0000 đến 1.0000.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/fusion/engine.py:L15-L160`.

---

#### F-10: Chính sách Quyết định Phán quyết (Decision Policy)
- **A. Định danh:** `F-10` | Fusion Core | Phân loại mẫu vào phán quyết an ninh cuối cùng (PASS, ALERT, QUARANTINE) dựa trên ngưỡng khoa học | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Thành phần pipeline tự động.
- **C. Điều kiện thực hiện:** Đã có `malware_score` và `suspicion_score`.
- **D. Input:** `suspicion_score`, `malware_score`, cờ cấu hình `demo_mode`, ngưỡng `alert_threshold` và `quarantine_threshold`.
- **E. Xử lý nghiệp vụ:**
  1. Nếu `demo_mode == True`:
     - Trả về phán quyết chính thức: `DEMO_ONLY`.
     - Tính toán thêm phán quyết ứng viên (candidate verdict) để người dùng tham khảo:
       - Nếu $\text{suspicion} \ge 0.35$ hoặc $\text{malware} \ge 0.85$ -> Ứng viên là `QUARANTINE`.
       - Nếu $\text{suspicion} \ge 0.10$ hoặc $\text{malware} \ge 0.50$ -> Ứng viên là `ALERT`.
       - Ngược lại -> Ứng viên là `PASS`.
  2. Nếu chạy chế độ khoa học thực thụ (`demo_mode == False`):
     - So sánh với ngưỡng đã hiệu chuẩn: Nếu $\ge \tau_{quarantine}$ (mặc định 0.85) -> `QUARANTINE`.
     - Nếu $\ge \tau_{alert}$ (mặc định D1 $\tau = 0.46885$) -> `ALERT`.
     - Ngược lại -> `PASS`.
- **F. Output:** `DecisionResult(decision="...", candidate_verdict="...", threshold_applied=float, warnings=list[str])`.
- **G. Ngoại lệ:** `RuntimeError` nếu chạy chế độ production khoa học nhưng chưa đóng băng ngưỡng (`threshold is None`).
- **H. Frontend implications:** 
  - Banner kết quả nổi bật ở đầu trang:
    - **Xanh lá (PASS):** Mẫu sạch, không phát hiện backdoor.
    - **Vàng cam (ALERT):** Phát hiện bất thường, yêu cầu SOC Analyst điều tra.
    - **Đỏ đậm (QUARANTINE):** Mẫu cực kỳ nguy hiểm, tự động cô lập.
    - **Xám viền vàng (DEMO_ONLY):** Chế độ thử nghiệm.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/fusion/decision.py:L15-L158`.

---

### PHÂN HỆ 2: RAW PE BINARY PROCESSING (F-11 & F-12)

#### F-11: Trích xuất Đặc trưng PE Tĩnh (Phase 2 LIEF Extractor)
- **A. Định danh:** `F-11` | Data / Raw PE | Phân tích tệp thực thi PE nhị phân tĩnh để sinh vector 2.381 chiều mà không cần chạy file | Trạng thái: `IMPLEMENTED_UNTESTED` | Ưu tiên: `P2`.
- **B. Người sử dụng:** Dành riêng cho chế độ mở rộng tương lai (Admin phê duyệt).
- **C. Điều kiện thực hiện:** Tệp nhị phân có kích thước $\le 50\text{ MB}$.
- **D. Input:** Luồng byte nhị phân của tệp EXE/DLL.
- **E. Xử lý nghiệp vụ:** Đọc headers COFF, mảng sections, import table bằng bộ phân tích cú pháp an toàn, trích xuất đúng 2.381 đặc trưng tương đương EMBER. Tuyệt đối không gọi `LoadLibrary` hay bất kỳ hàm thực thi nào của OS.
- **F. Output:** Vector 2.381 chiều sạch.
- **G. Ngoại lệ:** Tệp hỏng (`MalformedPEError`), kích thước vượt quá 50MB (`FileTooLargeError`).
- **H. Frontend implications:** Chưa dùng trực tiếp trong giao diện chính thức.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/data/raw_pe.py:L25-L350`.

---

#### F-12: Khóa An toàn Cổng Nạp Tệp PE Thô (Raw PE Fail-Closed Gate)
- **A. Định danh:** `F-12` | Security / API | Khóa chặt endpoint tải tệp nhị phân nhằm tuân thủ quy định an toàn của Change Control Board | Trạng thái: `DISABLED_BY_DESIGN` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Bất kỳ người dùng nào cố gắng gọi `POST /v1/analyze/file`.
- **C. Điều kiện thực hiện:** Luôn luôn kích hoạt ở chế độ V3 MVP.
- **D. Input:** Yêu cầu HTTP tới `/v1/analyze/file`.
- **E. Xử lý nghiệp vụ:** Chặn đứng ngay tại controller, ném HTTP 501 `XS_FEATURE_DISABLED` có giải thích rõ ràng "raw PE/LIEF is Phase 2".
- **F. Output:** `HTTP 501 Not Implemented`.
- **G. Ngoại lệ:** Luôn trả về 501.
- **H. Frontend implications:** Trên tab nạp dữ liệu, khu vực kéo thả tệp nhị phân EXE/DLL phải ở trạng thái **Disabled**, hiển thị biểu tượng ổ khóa màu xám kèm thông báo: *"Tính năng nạp tệp nhị phân trực tiếp đang được khóa an toàn (Pha 2). Vui lòng sử dụng vector đặc trưng EMBER đã giải nén."*
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/api/routes.py:L208-L218`, `tests/security/test_raw_pe_disabled.py:L1-L15`.

---

### PHÂN HỆ 3: AUDIT & EVIDENCE INTEGRITY (F-13 ĐẾN F-15)

#### F-13: Sinh Bằng chứng Pháp chứng Canonical Evidence (Canonical Evidence Generation)
- **A. Định danh:** `F-13` | Audit & Integrity | Tạo lập gói dữ liệu bằng chứng pháp chứng bất biến 19 trường có băm mật mã RFC 8785 | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Kích hoạt tự động khi hoàn thành phân tích.
- **C. Điều kiện thực hiện:** Có kết quả từ Lõi phát hiện và Fusion Engine.
- **D. Input:** Toàn bộ tham số phân tích: `request_id`, `run_id`, `input_id`, `malware_score`, `signals`, `fusion_score`, `decision`, `latencies`.
- **E. Xử lý nghiệp vụ:**
  1. Đóng gói vào frozen dataclass `CanonicalEvidence` gồm đúng 19 trường chuẩn.
  2. Chuẩn hóa JSON theo đặc tả RFC 8785 (sắp xếp khóa từ điển theo thứ tự từ điển, không khoảng trắng dư thừa, mã hóa UTF-8).
  3. Tính toán hàm băm SHA-256 trên chuỗi byte chuẩn hóa để sinh `evidence_hash`.
  4. Ghi nguyên tử vào kho bằng chứng tệp `.jsonl` và bảng `artifacts` trong SQL Server.
- **F. Output:** Đối tượng `CanonicalEvidence` đã đóng dấu băm SHA-256.
- **G. Ngoại lệ:** `AuditWriteFailureError` (`XS_AUDIT_WRITE_FAILED`) nếu ghi tệp thất bại, tự động kích hoạt rollback transaction DB.
- **H. Frontend implications:** Cung cấp nút bấm "Tải xuống Bằng chứng Pháp chứng (Download Evidence JSON)" trên màn hình kết quả để chuyên viên lưu trữ làm tư liệu pháp lý.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/audit/evidence.py:L40-L150`, `backend/src/x_sentinel/audit/writer.py:L20-L85`.

---

#### F-14: Ghi Nhật ký Bất biến (Append-Only Audit Logging)
- **A. Định danh:** `F-14` | Audit & Integrity | Ghi nhận toàn bộ sự kiện hệ thống vào bảng nhật ký chỉ ghi (Append-Only) | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Hệ thống nội bộ tự động ghi nhận khi có hành động nhạy cảm.
- **C. Điều kiện thực hiện:** Phiên làm việc CSDL hoạt động.
- **D. Input:** `event_type`, `user_id`, `entity_type`, `entity_id`, `payload (JSON)`.
- **E. Xử lý nghiệp vụ:** Thực hiện thao tác `INSERT` vào bảng `audit_events`. Cấm hoàn toàn các thao tác `UPDATE` hoặc `DELETE` trên bảng này ở cấp độ ứng dụng.
- **F. Output:** Bản ghi nhật ký mới với khóa chính tự tăng `BigInteger`.
- **G. Ngoại lệ:** Lỗi CSDL ném `SQLAlchemyError`.
- **H. Frontend implications:** Không hiển thị form chỉnh sửa. Cung cấp màn hình tra cứu Audit Trail cho vai trò Admin.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/database/repositories/audit_event.py:L15-L55`.

---

#### F-15: Tra cứu và Xác minh Tính toàn vẹn Bằng chứng (Evidence Verification & Retrieval)
- **A. Định danh:** `F-15` | Audit & Evidence | Lấy gói bằng chứng theo mã phân tích và kiểm tra chữ ký băm SHA-256 theo thời gian thực | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P1`.
- **B. Người sử dụng:** Analyst, Evaluator, Admin có quyền `evidence:read`.
- **C. Điều kiện thực hiện:** Người dùng sở hữu bản ghi phân tích hoặc có vai trò Admin/Evaluator.
- **D. Input:** `analysis_id` (UUID hoặc chuỗi `request_id`) truyền qua URL path.
- **E. Xử lý nghiệp vụ:**
  1. Kiểm tra quyền sở hữu bản ghi qua `assert_job_ownership()`. Nếu vi phạm ném HTTP 403 `XS_FORBIDDEN`.
  2. Nạp bản ghi bằng chứng từ kho lưu trữ.
  3. Thực hiện `evidence.verify_integrity()`: Tính lại mã băm RFC 8785 và so sánh với trường `evidence_hash` đã lưu.
  4. Nếu không khớp (bị chỉnh sửa ngoài luồng) -> Ném `EvidenceIntegrityError`.
- **F. Output:** `CanonicalEvidenceResponse` đầy đủ 19 trường kèm cờ `verified: true`.
- **G. Ngoại lệ:**
  - `HTTP 403 Forbidden` (`XS_FORBIDDEN`): Cố tình truy cập bằng chứng của người khác.
  - `HTTP 404 Not Found` (`XS_EVIDENCE_NOT_FOUND`): Không tìm thấy bằng chứng.
  - `HTTP 409 Conflict` (`XS_EVIDENCE_INTEGRITY_MISMATCH`): Bằng chứng bị sai lệch chữ ký băm (tampered).
- **H. Frontend implications:** Hiển thị huy hiệu xanh "✓ Hash Verified (RFC 8785)" nếu toàn vẹn; hiển thị cảnh báo đỏ nguy cấp nếu phát hiện sai lệch băm.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/services/evidence_service.py:L25-L95`, `backend/src/x_sentinel/api/routes.py:L303-L338`.

---

### PHÂN HỆ 4: HISTORY MANAGEMENT (F-16 ĐẾN F-18)

#### F-16: Xem Danh sách Lịch sử Phân tích & Lọc đa tiêu chí (Analysis History Listing)
- **A. Định danh:** `F-16` | History Management | Xem danh sách các yêu cầu phân tích đã thực hiện với phân trang và bộ lọc | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Operator, Analyst, Evaluator, Admin có quyền `analysis:read`.
- **C. Điều kiện thực hiện:** Đã đăng nhập. Người dùng thường chỉ thấy công việc của chính mình; Admin thấy toàn bộ.
- **D. Input (Query Parameters):**
  - `limit` (`int`, mặc định 50, từ 1 đến 1.000): Số lượng bản ghi trên một trang.
  - `offset` (`int`, mặc định 0, $\ge 0$): Vị trí bắt đầu bản ghi.
  - `status` (`str`, tùy chọn): Lọc theo trạng thái (`queued`, `running`, `completed`, `failed`, `quarantined`).
  - `decision` (`str`, tùy chọn): Lọc theo phán quyết (`pass`, `alert`, `quarantine`).
  - `input_mode` (`str`, tùy chọn): Lọc theo chế độ nạp (`vector`, `raw_pe`).
  - `demo_mode` (`bool`, tùy chọn): Lọc theo cờ demo mode (`true` / `false`).
- **E. Xử lý nghiệp vụ:**
  1. Xác định ngữ cảnh người dùng: Nếu không phải Admin, tự động chèn mệnh đề `WHERE user_id = current_user.id`.
  2. Truy vấn kết hợp bảng `analysis_jobs` và `analysis_results`.
  3. Đếm tổng số bản ghi thỏa mãn điều kiện phục vụ phân trang.
- **F. Output:** `AnalysisHistoryListResponse(items=list[AnalysisJobSummary], total=int, limit=int, offset=int)`.
- **G. Ngoại lệ:** `HTTP 401 Unauthenticated` nếu thiếu token.
- **H. Frontend implications:** Bảng dữ liệu lớn (DataTable) có thanh công cụ lọc thả xuống, ô tìm kiếm theo Request ID, phân trang chuẩn (First, Prev, Next, Last) và Skeleton Loading khi chuyển trang.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/services/history_service.py:L45-L101`, `backend/src/x_sentinel/api/routes.py:L225-L268`.

---

#### F-17: Xem Chi tiết Bản ghi Phân tích & Forensic Data (Analysis Detail Retrieval)
- **A. Định danh:** `F-17` | History Management | Xem toàn bộ chi tiết điểm số, chẩn đoán M1–M5, cảnh báo và thời gian thực thi của một job | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Operator, Analyst, Evaluator, Admin.
- **C. Điều kiện thực hiện:** Người dùng sở hữu job hoặc là Admin/Evaluator.
- **D. Input:** `analysis_id` (UUID hoặc chuỗi `request_id`) trên đường dẫn URL.
- **E. Xử lý nghiệp vụ:**
  1. Tìm kiếm job trong CSDL theo UUID hoặc `request_id`.
  2. Kiểm tra quyền sở hữu qua `assert_job_ownership()`.
  3. Lấy kết hợp kết quả phân tích (`analysis_results`), danh sách điểm số chi tiết từng detector (`detector_scores`), danh sách cảnh báo liên đới (`alerts`), và mã băm bằng chứng (`artifacts`).
- **F. Output:** `AnalysisDetailResponse` chứa toàn bộ cây dữ liệu phân tích.
- **G. Ngoại lệ:**
  - `HTTP 403 Forbidden` (`XS_FORBIDDEN`): Truy cập job của người khác khi không có quyền Admin.
  - `HTTP 404 Not Found` (`XS_ANALYSIS_NOT_FOUND`): Không tìm thấy job.
- **H. Frontend implications:** Màn hình trang chi tiết `/analysis/{id}` bao gồm các tabs: Tổng quan (Overview), Giải thích chuyên sâu (Explainability), Cảnh báo liên quan (Alerts), và Khung AI Cố vấn (Jev AI).
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/services/history_service.py:L103-L175`, `backend/src/x_sentinel/api/routes.py:L270-L297`.

---

#### F-18: Bảo vệ Quyền sở hữu Bản ghi Chống BOLA/IDOR (Object Ownership Enforcement)
- **A. Định danh:** `F-18` | Security / Auth | Ngăn chặn các lỗ hổng truy cập đối tượng trái phép (Broken Object Level Authorization / Insecure Direct Object References) | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Cơ chế phòng thủ tự động cho mọi API đọc chi tiết (`/v1/analysis/{id}`, `/v1/analysis/{id}/evidence`, `/v1/ai/runs/{id}`).
- **C. Điều kiện thực hiện:** Chế độ xác thực Bearer được kích hoạt (`XS_API_AUTH_MODE=bearer`).
- **D. Input:** Đối tượng bản ghi CSDL và danh tính người dùng `AuthUser`.
- **E. Xử lý nghiệp vụ:**
  1. Nếu người dùng là `admin` hoặc `evaluator` (cho phép trong kiểm thử) -> Cấp quyền truy cập.
  2. Nếu bản ghi có `user_id` khác với `current_user.id` -> Ném ngay `ObjectAccessDeniedError` (HTTP 403 `XS_FORBIDDEN`).
- **F. Output:** Không có (cho phép thực thi tiếp nếu hợp lệ).
- **G. Ngoại lệ:** `HTTP 403 Forbidden` (`XS_FORBIDDEN`: "Access denied: resource belongs to another user").
- **H. Frontend implications:** Khi nhận mã lỗi `XS_FORBIDDEN`, giao diện hiển thị màn hình 403 thân thiện: *"Bạn không có quyền truy cập bản ghi phân tích này vì nó thuộc quyền sở hữu của chuyên viên khác"*, kèm nút quay lại danh sách Lịch sử.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/security/auth.py:L279-L300`, `backend/tests/test_be15_security_rbac_blind.py:L60-L115`.

---

### PHÂN HỆ 5: SOC ALERT MANAGEMENT (F-19 ĐẾN F-21)

#### F-19: Xem Danh sách Cảnh báo SOC & Lọc (SOC Alerts Listing)
- **A. Định danh:** `F-19` | Alert Management | Trung tâm điều hành an ninh (SOC Console) hiển thị toàn bộ cảnh báo phát hiện backdoor | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Operator, Analyst, Admin có quyền `alerts:read`.
- **C. Điều kiện thực hiện:** Đã đăng nhập.
- **D. Input (Query Parameters):**
  - `limit` (`int`, mặc định 50, 1–1.000).
  - `offset` (`int`, mặc định 0, $\ge 0$).
  - `severity` (`str`, tùy chọn): Lọc mức độ nghiêm trọng (`low`, `medium`, `high`, `critical`).
  - `status` (`str`, tùy chọn): Lọc trạng thái xử lý (`open`, `acknowledged`, `resolved`, `dismissed`).
  - `analysis_job_id` (`str`, tùy chọn): Lọc theo UUID của job phát sinh cảnh báo.
- **E. Xử lý nghiệp vụ:** Truy vấn bảng `alerts`, sắp xếp theo thời gian tạo giảm dần (`created_at DESC`), hỗ trợ phân trang chuẩn.
- **F. Output:** `AlertListResponse(items=list[AlertSummary], total=int, limit=int, offset=int)`.
- **G. Ngoại lệ:** `HTTP 401 Unauthenticated` nếu thiếu token.
- **H. Frontend implications:** Màn hình bảng điều khiển SOC (`/alerts`) với các thẻ đếm nhanh số lượng cảnh báo theo mức độ (ví dụ: 3 Critical, 5 High, 12 Open) và bảng danh sách có huy hiệu màu phân cấp rõ ràng.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/services/alert_service.py:L33-L58`, `backend/src/x_sentinel/api/routes.py:L345-L384`.

---

#### F-20: Xem Chi tiết Cảnh báo Đơn lẻ (Alert Detail Retrieval)
- **A. Định danh:** `F-20` | Alert Management | Tra cứu thông tin chi tiết một cảnh báo theo mã UUID | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P1`.
- **B. Người sử dụng:** Operator, Analyst, Admin.
- **C. Điều kiện thực hiện:** Alert tồn tại trong hệ thống.
- **D. Input:** `alert_id` (UUID) trên URL path.
- **E. Xử lý nghiệp vụ:** Đọc bản ghi từ bảng `alerts` theo UUID.
- **F. Output:** `AlertSummary` gồm mã alert, mã job liên đới, mức độ, trạng thái, lý do phát sinh, thời gian tạo và thời gian giải quyết.
- **G. Ngoại lệ:** `HTTP 404 Not Found` (`XS_ALERT_NOT_FOUND`) nếu không tồn tại.
- **H. Frontend implications:** Hiển thị trong Drawer bên phải hoặc Modal khi người dùng nhấp vào một dòng trong bảng cảnh báo.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/services/alert_service.py:L60-L71`, `backend/src/x_sentinel/api/routes.py:L386-L407`.

---

#### F-21: Cập nhật Vòng đời Trạng thái Cảnh báo (Alert Status Mutation & Audit)
- **A. Định danh:** `F-21` | Alert Management | Cho phép chuyên viên SOC thay đổi trạng thái xử lý cảnh báo và tự động ghi nhật ký kiểm toán | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Analyst, Admin có quyền `alerts:mutate`. Operator không có quyền này.
- **C. Điều kiện thực hiện:** Người dùng có quyền; chuỗi trạng thái mới hợp lệ.
- **D. Input:**
  - `alert_id` (UUID trên path).
  - Request body: `{"status": "acknowledged" | "resolved" | "dismissed"}`.
- **E. Xử lý nghiệp vụ:**
  1. Kiểm tra trạng thái mới có thuộc danh sách hợp lệ không (`open`, `acknowledged`, `resolved`, `dismissed`).
  2. Nếu chuyển sang `resolved`: Cập nhật trường `resolved_at = sysdatetimeoffset()`.
  3. Cập nhật trạng thái trong bảng `alerts`.
  4. Tự động thêm một bản ghi vào bảng `audit_events` với `event_type = "alert.status_updated"` ghi lại danh tính chuyên viên thực hiện, trạng thái cũ và trạng thái mới.
  5. Commit giao dịch nguyên tử.
- **F. Output:** `AlertSummary` đã cập nhật trạng thái mới.
- **G. Ngoại lệ:**
  - `HTTP 400 Bad Request` (`XS_INVALID_TRANSITION`): Trạng thái mới không hợp lệ.
  - `HTTP 403 Forbidden` (`XS_FORBIDDEN`): Vai trò Operator cố tình thay đổi trạng thái.
  - `HTTP 404 Not Found` (`XS_ALERT_NOT_FOUND`): Alert không tồn tại.
- **H. Frontend implications:** Hộp thoại xác nhận (Confirm Dialog) trước khi chuyển trạng thái (đặc biệt khi Dismiss hoặc Resolve cảnh báo Critical). Cung cấp menu hành động nhanh (Quick Actions) trên từng dòng của bảng.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/services/alert_service.py:L73-L109`, `backend/src/x_sentinel/api/routes.py:L410-L442`.

---

### PHÂN HỆ 6: JEV AI ADVISORY COLLABORATION (F-22 ĐẾN F-25)

#### F-22: Kiểm tra Trạng thái Runtime Jev AI (Jev AI Status Probe)
- **A. Định danh:** `F-22` | Jev AI Advisory | Thăm dò trạng thái kết nối tới LM Studio cục bộ mà không gây gián đoạn hệ thống | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P1`.
- **B. Người sử dụng:** Tất cả người dùng và hệ thống giám sát.
- **C. Điều kiện thực hiện:** Không yêu cầu đăng nhập.
- **D. Input:** Không có (GET request tới `/v1/ai/status`).
- **E. Xử lý nghiệp vụ:**
  1. Kiểm tra cờ cấu hình `XS_JEV_AI_ENABLED`. Nếu `False` -> Trả về `status: "disabled"`.
  2. Nếu `True`, gửi yêu cầu probe nhẹ tới LM Studio `GET /v1/models`.
  3. Nếu kết nối thành công -> Trả về `status: "available"` kèm tên mô hình.
  4. Nếu kết nối thất bại hoặc timeout -> Trả về `status: "unavailable"` kèm thông báo lỗi ngắn gọn.
  5. **Bất biến:** Kết quả probe AI không bao giờ làm Backend trả về lỗi 500 hay làm sập hệ thống phát hiện chính.
- **F. Output:** `JevStatusResponse(enabled=bool, status="disabled"|"available"|"unavailable", advisory_only=True, model_id=str, prompt_version=str)`.
- **G. Ngoại lệ:** Luôn trả về 200 OK với trạng thái tương ứng.
- **H. Frontend implications:** Hiển thị biểu tượng trạng thái Jev AI ở góc trên bên phải thanh Header (Xanh nếu Available, Vàng nếu Disabled, Xám nếu Offline) để chuyên viên biết trước khi bấm nút yêu cầu giải thích.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/jev_ai/status.py:L15-L65`, `backend/src/x_sentinel/api/routes.py:L134-L143`.

---

#### F-23: Thực thi Luồng Cố vấn AI (Execute Jev AI Advisory Workflow)
- **A. Định danh:** `F-23` | Jev AI Advisory | Điều phối 4 chế độ suy luận an ninh chuyên sâu (Explain, Triage, Compare, Report) hoàn toàn mang tính tư vấn | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Analyst, Admin có quyền `ai:invoke`. Operator không có quyền.
- **C. Điều kiện thực hiện:** 
  - Yêu cầu bản ghi phân tích gốc (`analysis_id`) đã tồn tại trong CSDL và có bằng chứng pháp chứng nguyên vẹn.
  - Chế độ `compare` bắt buộc cung cấp thêm `compare_with_analysis_id`.
  - Bộ giới hạn lưu lượng AI cho phép tiếp nhận (<4 tác vụ đồng thời, hàng đợi <16).
- **D. Input (JSON Body):**
  - `analysis_id` (`str`, bắt buộc): UUID hoặc Request ID của mẫu phân tích.
  - `mode` (`str`, mặc định `"explain"`): Chọn 1 trong 4 chế độ: `explain`, `triage`, `compare`, `report`.
  - `compare_with_analysis_id` (`str`, tùy chọn): Bắt buộc khi mode là `compare`.
  - `focus_signals` (`list[str]`, tùy chọn): Danh sách tín hiệu cần tập trung (tối đa 5 phần tử: `m1`..`m5`).
  - `question` (`str`, tùy chọn): Câu hỏi cụ thể của chuyên viên (tối đa 500 ký tự).
- **E. Xử lý nghiệp vụ:**
  1. Kiểm tra tính toàn vẹn của bằng chứng pháp chứng gốc qua `verify_integrity()`.
  2. Nạp dữ liệu qua `Safe Context Builder`: Loại bỏ mọi trường nhạy cảm, băm vector, cắt ngắn văn bản $\le 30.000$ ký tự.
  3. Quét phát hiện tấn công Prompt Injection (`check_prompt_injection`). Nếu phát hiện chuỗi độc hại -> Ném `JevPromptInjectionBlocked` (HTTP 422).
  4. Quét chống rò rỉ dữ liệu mật (`check_blind_data_in_text`).
  5. Gọi LM Studio qua loopback HTTP client.
  6. Áp dụng chuẩn hóa Softmax trên Logprobs phân phối xác suất.
  7. Lưu kết quả vào bảng `jev_ai_runs` với cờ `advisory_only: True` và `authoritative_decision_unchanged: True`.
- **F. Output:** `JevAIRunResponse` chứa định danh `id`, lời văn phân tích `response_text`, cấu trúc quyết định `decision_result`, độ trễ `latency_ms`, mã băm ngữ cảnh đầu vào và đầu ra.
- **G. Ngoại lệ:**
  - `HTTP 403 Forbidden` (`XS_FORBIDDEN`): Phân tích thuộc về chuyên viên khác.
  - `HTTP 404 Not Found` (`XS_ANALYSIS_NOT_FOUND`): Không tìm thấy bản ghi phân tích.
  - `HTTP 409 Conflict` (`XS_EVIDENCE_INTEGRITY_MISMATCH`): Bằng chứng máy bị sai lệch băm.
  - `HTTP 422 Unprocessable Entity` (`XS_AI_CONTEXT_BLOCKED`): Phát hiện prompt injection.
  - `HTTP 429 Too Many Requests` (`XS_AI_OVERLOADED`): Hàng đợi AI quá tải (>16 yêu cầu).
  - `HTTP 503 Service Unavailable` (`XS_AI_DISABLED` hoặc `XS_AI_UNAVAILABLE`): LM Studio tắt hoặc cấu hình AI bị tắt.
  - `HTTP 504 Gateway Timeout` (`XS_AI_TIMEOUT`): LM Studio không phản hồi sau 60 giây.
- **H. Frontend implications:** Giao diện Jev AI Studio chuyên biệt trong Drawer/Tab. Cho phép chọn Mode qua Segmented Control. Có ô nhập câu hỏi chuyên viên. Hiển thị Skeleton Loading dạng typing khi AI đang suy luận. Render Markdown an toàn kèm thanh phân phối xác suất Logprob (ví dụ: Backdoor Detected: 94.2%, Clean: 5.8%).
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/services/jev_ai_service.py:L185-L390`, `backend/src/x_sentinel/jev_ai/orchestrator.py:L45-L210`.

---

#### F-24: Thu thập và Xem Phản hồi Đánh giá AI (Jev AI Feedback Collection)
- **A. Định danh:** `F-24` | Jev AI Advisory | Cho phép chuyên viên an ninh đánh giá chất lượng phản hồi của AI để cải tiến mô hình | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P1`.
- **B. Người sử dụng:** Analyst, Admin có quyền `ai:feedback`.
- **C. Điều kiện thực hiện:** Lượt chạy AI (`run_id`) đã hoàn thành ở trạng thái kết thúc (`completed`, `failed`, hoặc `blocked`). Mỗi người dùng chỉ được gửi feedback 1 lần cho mỗi lượt chạy.
- **D. Input:**
  - `run_id` (UUID trên path).
  - Request body:
    - `rating` (`int`, tùy chọn): Đánh giá sao từ 1 đến 5 (bắt buộc số nguyên nghiêm ngặt, từ chối boolean/string).
    - `label` (`str`, tùy chọn): Chọn 1 trong 5 nhãn: `helpful`, `not_helpful`, `incorrect`, `unsafe`, `unclear`.
    - `comment` (`str`, tùy chọn): Nhận xét của chuyên viên (tối đa 2.000 ký tự).
- **E. Xử lý nghiệp vụ:**
  1. Kiểm tra lượt chạy AI tồn tại.
  2. Kiểm tra tính kết thúc: Nếu run đang ở trạng thái `queued` hoặc `running` -> Ném `HTTP 409 XS_AI_RUN_NOT_TERMINAL`.
  3. Kiểm tra trùng lặp: Nếu chuyên viên đã gửi feedback trước đó -> Ném `HTTP 409 XS_DUPLICATE_FEEDBACK`.
  4. Lưu bản ghi vào bảng `jev_ai_feedback`.
- **F. Output:** `JevFeedbackResponse(id=str, rating=int, label=str, comment=str, advisory_only=True)`.
- **G. Ngoại lệ:**
  - `HTTP 400 Bad Request` (`XS_FEEDBACK_INVALID`): Vi phạm validation (rating ngoài 1-5, comment > 2000 ký tự).
  - `HTTP 409 Conflict` (`XS_AI_RUN_NOT_TERMINAL` hoặc `XS_DUPLICATE_FEEDBACK`).
- **H. Frontend implications:** Khối đánh giá nhỏ gọn đặt ở cuối mỗi phản hồi của AI: 5 ngôi sao tương tác, nhóm nút chọn nhãn nhanh (Chips) và khung bình luận có nút gửi. Sau khi gửi hiển thị thông báo "Cảm ơn bạn đã phản hồi!".
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/services/jev_ai_service.py:L480-L580`, `backend/src/x_sentinel/api/routes.py:L541-L590`.

---

#### F-25: Hỏi đáp Tài liệu Hệ thống qua AI (Phase 2 Gated Docs QA)
- **A. Định danh:** `F-25` | Jev AI Advisory | Truy vấn hỏi đáp trực tiếp trên kho tài liệu dự án | Trạng thái: `DISABLED_BY_DESIGN` | Ưu tiên: `P2`.
- **B. Người sử dụng:** Bất kỳ ai gọi `POST /v1/ai/docs/ask`.
- **C. Điều kiện thực hiện:** Bị khóa an toàn kiểu đóng.
- **D. Input:** N/A.
- **E. Xử lý nghiệp vụ:** Trả về HTTP 501 `XS_FEATURE_DISABLED` thông báo tính năng dành cho Pha 2.
- **F. Output:** HTTP 501 JSON Envelope.
- **G. Ngoại lệ:** Luôn trả về 501.
- **H. Frontend implications:** Không hiển thị nút bấm này trên giao diện người dùng chính.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/api/routes.py:L592-L608`.

---

### PHÂN HỆ 7: SYSTEM OBSERVABILITY & TELEMETRY (F-26 ĐẾN F-28)

#### F-26: Kiểm tra Sức khỏe và Độ sẵn sàng Hệ thống (System Health & Readiness)
- **A. Định danh:** `F-26` | System Observability | Cung cấp endpoints phục vụ Kubernetes liveness/readiness probe và hiển thị banner trạng thái trên UI | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P0`.
- **B. Người sử dụng:** Công khai, không yêu cầu xác thực.
- **C. Điều kiện thực hiện:** Không có.
- **D. Input:** GET `/health` hoặc GET `/ready`.
- **E. Xử lý nghiệp vụ:**
  1. `/health`: Trả về liveness cơ bản (`status: "ok"`, `demo_mode: bool`, `jev_ai_enabled: bool`).
  2. `/ready`: Kiểm tra kết nối CSDL SQL Server, kiểm tra phiên bản migration Alembic (`0002_v3_jev_ai_audit`), kiểm tra trạng thái cấu hình. Nếu có lỗi, liệt kê chi tiết trong mảng `blockers`. Trả về mã HTTP 200 nếu sẵn sàng, 503 nếu có blocker.
- **F. Output:** JSON payload chi tiết kèm danh sách blockers.
- **G. Ngoại lệ:** HTTP 503 khi CSDL chưa sẵn sàng hoặc cấu hình bị thiếu.
- **H. Frontend implications:** Frontend gọi `/health` và `/ready` khi khởi động ứng dụng. Nếu Backend chưa sẵn sàng, hiển thị màn hình cảnh báo toàn trang: *"Không thể kết nối tới Backend X-SENTINEL hoặc CSDL đang bảo trì"* kèm danh sách blockers.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/main.py:L95-L132`.

---

#### F-27: Kiểm tra Trạng thái Cấu hình & Phiên bản CSDL (Config Status Inspection)
- **A. Định danh:** `F-27` | System Observability | Cung cấp chi tiết các thông số môi trường không nhạy cảm phục vụ kiểm tra vận hành | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P1`.
- **B. Người sử dụng:** Công khai / Chuyên viên vận hành.
- **C. Điều kiện thực hiện:** Không có.
- **D. Input:** GET `/v1/config/status`.
- **E. Xử lý nghiệp vụ:** Tập hợp thông tin môi trường (`env`), chế độ (`demo_mode`), kiểu nạp dữ liệu (`input_mode`), tình trạng kết nối CSDL và thông số Jev AI (loại bỏ toàn bộ mật khẩu, chuỗi kết nối và API keys).
- **F. Output:** JSON payload an toàn.
- **G. Ngoại lệ:** N/A.
- **H. Frontend implications:** Hiển thị thẻ thông tin hệ thống trong trang Cài đặt / System Status.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/main.py:L134-L157`.

---

#### F-28: Giám sát Telemetry Phần cứng & Prometheus Metrics (Authentic Telemetry)
- **A. Định danh:** `F-28` | System Observability | Cung cấp số liệu đo lường phần cứng thực tế từ OS qua `psutil` và chuẩn metrics Prometheus | Trạng thái: `IMPLEMENTED_VERIFIED` | Ưu tiên: `P1`.
- **B. Người sử dụng:** Operator, Admin có quyền `admin:ops`.
- **C. Điều kiện thực hiện:** Người dùng có quyền; tính năng giám sát được bật trong cấu hình (`XS_PERFORMANCE_MONITORING_ENABLED=true`).
- **D. Input:** GET `/v1/system/telemetry` hoặc GET `/v1/system/metrics`.
- **E. Xử lý nghiệp vụ:**
  1. Sử dụng thư viện hệ thống `psutil` để đọc: Tỷ lệ sử dụng CPU thực tế (`cpu_percent`), bộ nhớ RAM khả dụng và đã dùng (`virtual_memory`), bộ nhớ tiến trình Backend đang chiếm dụng (`process_memory_rss_bytes`), số lượng luồng đang chạy (`num_threads`).
  2. Bất biến chống dữ liệu giả: Tuyệt đối không dùng dữ liệu giả lập (hardcoded / mock).
- **F. Output:** Dữ liệu JSON telemetry thực tế hoặc văn bản Prometheus text format.
- **G. Ngoại lệ:**
  - `HTTP 403 Forbidden`: Vai trò Analyst hoặc Operator không có quyền truy cập.
  - `HTTP 404 Not Found`: Khi tính năng bị tắt trong cấu hình.
- **H. Frontend implications:** Trang Quản trị Hệ thống (`/system/status`) hiển thị biểu đồ thời gian thực: Đồng hồ đo CPU (%), Thanh đo RAM (MB / GB), và biểu đồ lưu lượng API.
- **I. Bằng chứng mã nguồn:** `backend/src/x_sentinel/api/routes.py:L615-L660`, `infrastructure/monitoring/telemetry.py`.
