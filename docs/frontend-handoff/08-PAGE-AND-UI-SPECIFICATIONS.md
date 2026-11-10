# 08 — ĐẶC TẢ CHI TIẾT GIAO DIỆN & THIẾT KẾ UI/UX (PAGE AND UI SPECIFICATIONS)
## HỆ THỐNG X-SENTINEL V3 — MALWARE ANALYSIS & THREAT DETECTION PLATFORM

---

### MỤC LỤC
1. [Hệ Thống Thiết Kế & Quy Chuẩn Đo Lường Impeccable (Design System Tokens)](#1-hệ-thống-thiết-kế--quy-chuẩn-đo-lường-impeccable-design-system-tokens)
2. [Khung Bố Cục Nền Tảng (Master Shell & Layout Framework)](#2-khung-bố-cục-nền-tảng-master-shell--layout-framework)
3. [Đặc Tả Bố Cục & Tương Tác Từng Màn Hình](#3-đặc-tả-bố-cục--tương-tác-từng-màn-hình)
   - [P01 — `/analyze` (Nộp Mẫu Phân Tích PE)](#p01--analyze-nộp-mẫu-phân-tích-pe)
   - [P02 — `/analysis/{id}` (Hero Phán Quyết & Canonical Evidence)](#p02--analysisid-hero-phán-quyết--canonical-evidence)
   - [P03 — `/analysis/{id}/explainability` (XAI SHAP Waterfall Plot)](#p03--analysisidexplainability-xai-shap-waterfall-plot)
   - [P04 — `/analysis/{id}/ai-advisory` (Khung Khuyến Nghị Jev AI & MITRE ATT&CK)](#p04--analysisidai-advisory-khung-khuyến-nghị-jev-ai--mitre-attck)
   - [P05 — `/history` (Bảng Dữ Liệu Lịch Sử & Lọc Nâng Cao)](#p05--history-bảng-dữ-liệu-lịch-sử--lọc-nâng-cao)
   - [P06 & P07 — `/alerts` & `/alerts/{id}` (SOC Triage & Workflow Stepper)](#p06--p07--alerts--alertsid-soc-triage--workflow-stepper)
   - [P08 — `/system/status` (Authentic Telemetry Dashboard từ `psutil`)](#p08--systemstatus-authentic-telemetry-dashboard-từ-psutil)
   - [P09 & P10 — `/evaluation` & `/auth/switch` (Benchmark & Dev Switcher)](#p09--p10--evaluation--authswitch-benchmark--dev-switcher)
4. [Trạng Thái Tải, Lỗi & Phản Hồi Vi Tương Tác (Loading, Error & Interaction States)](#4-trạng-thái-tải-lỗi--phản-hồi-vi-tương-tác-loading-error--interaction-states)

---

### 1. HỆ THỐNG THIẾT KẾ & QUY CHUẨN ĐO LƯỜNG IMPECCABLE (DESIGN SYSTEM TOKENS)

Hệ thống Frontend X-SENTINEL V3 tuân thủ nghiêm ngặt **Tiêu chuẩn Thiết kế Impeccable** và **Bộ 5 Định luật Tâm lý UI/UX Bất biến**, triệt tiêu hoàn toàn giao diện khuôn mẫu giả tạo (AI-slop) nhằm tạo ra trải nghiệm công cụ tác chiến an ninh mạng đẳng cấp thế giới.

#### 1.1. Bảng Mã Màu Cao Cấp (Calibrated Color Palette)
> [!IMPORTANT]
> **CẤM TUYỆT ĐỐI** sử dụng Pure Black (`#000000`) và Pure White (`#ffffff`). Toàn bộ giao diện sử dụng các gam màu tối sâu sắc nét (Deep Slate / Dark Charcoal) và bề mặt sáng dịu nhẹ có độ tương phản đạt chuẩn WCAG AAA (tối thiểu 7:1 cho văn bản chính và 4.5:1 cho thành phần đồ họa).

| Tên Token (Design Token) | Giá trị Hex (Dark Mode) | Giá trị Hex (Light Mode) | Mục đích sử dụng |
|:---|:---|:---|:---|
| `--color-bg-base` | `#121418` (Obsidian Deep) | `#f4f6f8` (Soft Off-White) | Nền toàn bộ ứng dụng |
| `--color-bg-surface` | `#181b20` (Dark Slate) | `#ffffff` -> `#fbfcfd` (Ivory Crisp) | Bề mặt card, modal, bảng dữ liệu |
| `--color-bg-subtle` | `#20252d` (Muted Slate) | `#edf0f4` (Light Neutral) | Nền ô nhập liệu, bảng phụ |
| `--color-border-subtle` | `#29303b` | `#e2e6eb` | Viền ngăn cách thông thường |
| `--color-border-prominent`| `#3b4554` | `#cbd2dc` | Viền khung card chính, viền input hover |
| `--color-text-primary` | `#f1f5f9` (Slate 100) | `#1a202c` (Slate 900) | Tiêu đề, số liệu chính, phán quyết |
| `--color-text-secondary` | `#94a3b8` (Slate 400) | `#4a5568` (Slate 600) | Nhãn thuộc tính, mô tả kỹ thuật |
| `--color-text-muted` | `#64748b` (Slate 500) | `#718096` (Slate 500) | Chú thích mốc thời gian, placeholder |
| `--color-accent-brand` | `#38bdf8` (Cyan Electric) | `#0284c7` (Sky Blue) | Tiêu điểm điều hướng, trạng thái active |
| `--color-verdict-malicious`| `#f43f5e` (Rose Danger) | `#e11d48` (Crimson Red) | Mã độc nguy hiểm, lỗi nghiêm trọng |
| `--color-verdict-suspicious`| `#f59e0b` (Amber Radiant) | `#d97706` (Amber Ochre) | Đáng ngờ, cảnh báo, Advisory Jev AI |
| `--color-verdict-benign` | `#10b981` (Emerald Pure) | `#059669` (Forest Green) | An toàn lành tính, thành công |

#### 1.2. Thang Đo Khoảng Cách (Spacing Tokens & Hierarchy)
Áp dụng **Định luật Gần gũi (Law of Proximity)**: Khoảng cách giữa các thành phần phản ánh quan hệ logic dữ liệu:
- `Space Internal (Label -> Input):` **`12px`** (hoặc `8px` cho mật độ cao).
- `Space Item (Input -> Input cùng nhóm):` **`16px`**.
- `Space Group (Nhóm chức năng -> Nhóm chức năng):` **`24px`**.
- `Space Section (Section -> Section):` **`32px`**.
- `Space Layout (Vùng làm việc -> Thanh điều hướng):` **`48px`**.

#### 1.3. Tỷ Lệ Đệm Nút Bấm & Quy Tắc Bo Góc Lồng Nhau (Button & Nested Radius)
- **Tỷ lệ đệm nút bấm chuẩn 2:1:**
  - Nút tiêu chuẩn (Medium Button): $Padding_Y = 10\text{px}$, $Padding_X = 20\text{px}$ (`py-2.5 px-5`).
  - Nút lớn (Large CTA): $Padding_Y = 14\text{px}$, $Padding_X = 28\text{px}$ (`py-3.5 px-7`).
  - Nút thu gọn (Compact/Table Action): $Padding_Y = 6\text{px}$, $Padding_X = 12\text{px}$ (`py-1.5 px-3`).
- **Quy tắc Bo góc lồng nhau (Nested Radius Invariant):**
  $$\text{Radius}_{\text{inner}} = \text{Radius}_{\text{outer}} - \text{Padding}_{\text{container}}$$
  *Ví dụ:* Card bên ngoài có `rounded-xl` ($12\text{px}$), đệm bên trong $Padding = 8\text{px}$, thì thành phần con bên trong (nút hoặc thẻ con) **BẮT BUỘC** có bán kính bo góc là $12 - 8 = 4\text{px}$ (`rounded-sm`), loại bỏ hiện tượng góc bị méo lệch thị giác.

---

### 2. KHUNG BỐ CỤC NỀN TẢNG (MASTER SHELL & LAYOUT FRAMEWORK)

Ứng dụng sử dụng cấu trúc Responsive Split Layout với Thanh điều hướng cố định (Persistent Left Sidebar), Thanh đầu trang tác chiến (Global Security Header) và Vùng nội dung chính cuộn độc lập (Scrollable Main Viewport).

```
+----------------------------------------------------------------------------------------------------+
|  [Logo X-SENTINEL]  X-SENTINEL V3  | Status: HEALTHY | Uptime: 14d 6h | [Role: ANALYST] [User: U01] |  <- Header (64px)
+----------------------------------------------------------------------------------------------------+
|  SIDEBAR (260px)   |  BREADCRUMB: Home > Analysis > #JOB-94a20f                                    |
|                    +-------------------------------------------------------------------------------+
|  [+] Run Analysis  |                                                                               |
|  [=] History       |   MAIN CONTENT WORKSPACE (Max Width: 1440px Centered)                         |
|  [!] Alert Center  |                                                                               |
|  [*] Telemetry     |   [ Hero Card / Form / Interactive Charts / Tables ]                          |
|  [^] Evaluation    |                                                                               |
|                    |                                                                               |
|  ----------------  |                                                                               |
|  [@] Switch Role   |                                                                               |
+--------------------+-------------------------------------------------------------------------------+
|  System Footer: Canonical Verdict Engine v3.0 | SHA-256 Hash Guard Active | Advisory Model: Local LLM (settings.jev_ai_model)|  <- Footer (32px)
+----------------------------------------------------------------------------------------------------+
```

---

### 3. ĐẶC TẢ BỐ CỤC & TƯƠNG TÁC TỪNG MÀN HÌNH

#### P01 — `/analyze` (NỘP MẪU PHÂN TÍCH PE)
- **Bố cục chính:** Single-Column Form tập trung cao độ, căn giữa màn hình ($Max Width = 840\text{px}$), tối ưu hóa trải nghiệm nộp mẫu không gây phân tâm.

```
+--------------------------------------------------------------------------------+
|  Trang Nộp Mẫu Phân Tích Mã Độc PE (PE Malware Analysis Submission)            |
|  Phân tích đa chiều kết hợp 5 Module Ensemble và Báo cáo Cố vấn Jev AI         |
+--------------------------------------------------------------------------------+
|  [ Tab 1: 2,381-Dim Feature Vector ] |  [ Tab 2: Raw PE Upload (Disabled) ]     |
+--------------------------------------------------------------------------------+
|  (!) CẢNH BÁO AN TOÀN HẠ TẦNG:                                                 |
|  Tính năng nộp tệp nhị phân thô tạm thời vô hiệu hóa theo chính sách an ninh   |
|  cách ly mạng (HTTP 501 XS_FEATURE_DISABLED). Vui lòng sử dụng Feature Vector. |
+--------------------------------------------------------------------------------+
|  Nạp Dữ Liệu Mẫu Nhanh:                                                        |
|  [ Nạp Mẫu Ransomware (WannaCry) ]  [ Nạp Mẫu Trojan ]  [ Nạp Mẫu Benign ]     |
+--------------------------------------------------------------------------------+
|  Dữ Liệu Feature Vector 2.381 Chiều (JSON Array 2.381 phần tử số thực 0.0-1.0):|
|  +--------------------------------------------------------------------------+  |
|  | [ 0.824, 0.129, 0.000, 0.941, 0.450, 0.021, 0.884, 0.112, ... ]          |  |
|  +--------------------------------------------------------------------------+  |
|  Độ dài hiện tại: 2.381/2.381 phần tử | Trạng thái: HỢP LỆ (VALID)             |
+--------------------------------------------------------------------------------+
|  Tùy Chọn Phân Tích Bổ Sung:                                                   |
|  [X] Kích hoạt Trợ lý Cố vấn Bảo mật Jev AI (Sinh báo cáo phản ứng sự cố)      |
|  Mức độ ưu tiên phân tích: [ Normal (Mặc định)                     [v] ]       |
+--------------------------------------------------------------------------------+
|  [ Tiêu hủy dữ liệu / Nhập lại ]        [ TIẾN HÀNH PHÂN TÍCH MẪU (RUN) -> ]   |
+--------------------------------------------------------------------------------+
```

- **Quy tắc Tương tác Form:**
  - Nhập mảng JSON: Kiểm tra realtime số lượng phần tử. Nếu khác 2.381 phần tử, hiển thị viền đỏ và dòng cảnh báo: `Yêu cầu chính xác 2.381 phần tử. Hiện có: X phần tử`.
  - Nút Nạp Mẫu Nhanh: 1-Click điền ngay bộ vector chuẩn hóa, tự động xóa lỗi validation.
  - Nút Hành động Primary: Kích thước lớn, màu thương hiệu nổi bật (`--color-accent-brand`), vô hiệu hóa khi form chưa hợp lệ.

---

#### P02 — `/analysis/{id}` (HERO PHÁN QUYẾT & CANONICAL EVIDENCE)
- **Bố cục chính:** Bố cục 2 cột bất đối xứng (Asymmetric Grid 8:4), đặt Phán quyết Canonical ở vị trí trung tâm thị giác tuyệt đối (**Định luật Von Restorff**).

```
+----------------------------------------------------------------------------------------------------+
|  Job ID: 94a20f51-789a-4e2a-89a1-0984cfb78912  | Status: COMPLETED | Thời gian: 2026-10-16 10:20:15 |
+----------------------------------------------------------------------------------------------------+
|  [ CỘT TRÁI: 8 PHẦN ]                               |  [ CỘT PHẢI: 4 PHẦN ]                        |
|                                                     |                                              |
|  +-----------------------------------------------+  |  +----------------------------------------+  |
|  | *** HERO VERDICT CARD ***                     |  |  | MÃ BĂM BẰNG CHỨNG (EVIDENCE HASH)      |  |
|  |                                               |  |  | SHA-256 Bất biến bảo vệ chứng cứ:      |  |
|  |      [ QUARANTINE (CÁCH LY MÃ ĐỘC) ]   |  |  | `e3b0c44298fc1c149afbf4c8996fb9242...` |  |
|  |  (Canonical: PASS / ALERT / QUARANTINE)|  |  [ Sao Chép Mã Băm ] [ Xuất JSON ]      |  |
|  |  Độ Tin Cậy: 98.7% (Very High Confidence)     |  |  +----------------------------------------+  |
|  |  Thời gian suy luận: 42ms | Queue Time: 3ms    |  |                                              |
|  +-----------------------------------------------+  |  +----------------------------------------+  |
|                                                     |  | THÔNG TIN QUYỀN SỞ HỮU (BOLA GUARD)    |  |
|  BẢNG PHÂN RÃ TRỌNG SỐ 5 MODULE (ENSEMBLE BREAKDOWN)|  |  Phân tích bởi: Chuyên viên SOC L2     |  |
|  +-----------------------------------------------+  |  Mã Người dùng: `usr-soc-analyst-01`      |  |
|  | Module                     | Điểm   | Đóng góp|  |  Quyền hạn: Độc quyền chủ sở hữu       |  |
|  |----------------------------+--------+---------|  |  +----------------------------------------+  |
|  | M1: TADR (Dominance Ratio) | 0.992  | 35.0%   |  |                                              |
|  | M2: Tabular STRIP (Entropy)| 0.884  | 20.0%   |  |  +----------------------------------------+  |
|  | M3: View Concentration     | 0.941  | 20.0%   |  |  | TÁC VỤ PHẢN ỨNG TỨC THỜI               |  |
|  | M4: Cross-View Disagreement| 0.760  | 15.0%   |  |  | [!] Phát Động Cảnh Báo SOC Khẩn Cấp    |  |
|  | M5: Semantic Plausibility  | 0.812  | 10.0%   |  |  | [>] Xem Giải Trình SHAP (/explain)     |  |
|  +-----------------------------------------------+  |  | [?] Khuyến Nghị Jev AI (/advisory)     |  |
|                                                     |  +----------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
```

---

#### P03 — `/analysis/{id}/explainability` (XAI SHAP WATERFALL PLOT) [STATUS: DESIGN_ONLY / BACKEND_GAP FOR PER-FEATURE SHAP]
- **Bố cục chính:** Bố cục phân tích trực quan toàn màn hình, tập trung giải mã "hộp đen" của mô hình AI.
- **Lưu ý dữ liệu Backend:** Endpoint `GET /v1/analysis/{id}` cung cấp chính xác `view_contributions` (3 Semantic Views) và chẩn đoán `scores` (M1–M5). Thành phần biểu đồ thác nước Top 15 SHAP features và bảng tra cứu 2.381 thuộc tính cá nhân dưới đây là thiết kế giao diện chuẩn bị sẵn (`DESIGN_ONLY` / `BACKEND_GAP`) đang chờ Backend mở rộng endpoint bóc tách mảng SHAP chi tiết.

```
+----------------------------------------------------------------------------------------------------+
|  < Quay lại Tổng quan Kết quả (#94a20f51)  |  GIẢI TRÌNH MÔ HÌNH HỌC MÁY (EXPLAINABLE AI - XAI)    |
|  [!] LƯU Ý: Biểu đồ Top SHAP dưới đây hiển thị dữ liệu Design Mock (Chờ Backend XAI API)          |
+----------------------------------------------------------------------------------------------------+
|  BIỂU ĐỒ ĐÓNG GÓP ĐẶC TRƯNG SHAP (TOP 15 FEATURES IMPACT) [DESIGN_ONLY / MOCK]                     |
|  Giá trị cơ sở E[f(x)] = 0.12 (Ngưỡng an toàn) ---> Kết quả f(x) = 0.987 (Mã độc cực kỳ nguy hiểm) |
|                                                                                                    |
|  Section .text Entropy (> 7.42)           [==================== +0.342 ] (Đỏ cam: Đẩy độc hại)     |
|  Import API: VirtualAllocEx               [=============== +0.218 ]                                |
|  Import API: WriteProcessMemory           [============= +0.194 ]                                  |
|  Rich Header Checksum Anomaly             [======== +0.102 ]                                       |
|  Valid Digital Signature (Microsoft Corp) [==== -0.065 ] (Xanh lục: Kéo về an toàn)                |
|  Standard PE Section Headers Count        [== -0.021 ]                                             |
|  ...                                                                                               |
+----------------------------------------------------------------------------------------------------+
|  BẢNG TRA CỨU TOÀN BỘ 2.381 ĐẶC TRƯNG PE INPUT:                                                    |
|  [ Ô tìm kiếm đặc trưng...                                    ] [ Lọc theo chiều tác động: Tất cả ]|
|  +-----------------------------------------------------------------------------------------------+ |
|  | Tên Đặc Trưng (Canonical Name) | Giá Trị Thô | Giá Trị Chuẩn Hóa | Tác Động SHAP | Trọng Số   | |
|  |--------------------------------+-------------+-------------------+---------------+------------| |
|  | section_entropy_text           | 7.842       | 0.980             | +0.342        | Rất Cao    | |
|  | import_api_virtualalloc        | 1.000       | 1.000             | +0.218        | Cao        | |
|  | pe_subsystem_windows_gui       | 2.000       | 0.200             | -0.012        | Thấp       | |
|  +-----------------------------------------------------------------------------------------------+ |
+----------------------------------------------------------------------------------------------------+
```

---

#### P04 — `/analysis/{id}/ai-advisory` (KHUNG KHUYẾN NGHỊ JEV AI & MITRE ATT&CK)
- **BẤT BIẾN THIẾT KẾ BẮT BUỘC:** Hiển thị viền vàng hổ phách bao bọc toàn bộ màn hình kèm Banner Cố vấn Tham khảo.

```
+----------------------------------------------------------------------------------------------------+
|  [!] KHUYẾN NGHỊ THAM KHẢO DUY NHẤT (ADVISORY ONLY)                                                |
|  Nội dung do Trợ lý AI Cố vấn Bảo mật Jev AI (Mô hình cục bộ qua settings.jev_ai_model) tự động tổng hợp|
|  tra. Nội dung này KHÔNG PHẢI phán quyết chính thức và KHÔNG CÓ GIÁ TRỊ PHÁP LÝ thay thế Canonical |
|  Evidence tại trang Tổng quan Kết quả.                                                             |
+----------------------------------------------------------------------------------------------------+
|  Trạng thái Cố vấn: HOÀN TẤT | Thời gian sinh: 1.4s | Tokens: 412 | [ Yêu Cầu Sinh Lại Nhận Định ]  |
+----------------------------------------------------------------------------------------------------+
|  BÁO CÁO NHẬN ĐỊNH HÀNH VI TỰ NHIÊN (THREAT NARRATIVE):                                            |
|  Mẫu PE được phân tích có nhiều dấu hiệu tương đồng với họ mã độc tống tiền (Ransomware) thế hệ mới.|
|  Mã độc thực hiện cấp phát bộ nhớ ảo tùy ý qua VirtualAllocEx, kết hợp với các section có entropy cao|
|  bất thường nhằm che giấu payload mã hóa tệp tin trước các giải pháp EDR truyền thống.             |
+----------------------------------------------------------------------------------------------------+
|  ÁNH XẠ MA TRẬN CHIẾN THUẬT MITRE ATT&CK:                                                          |
|  +-----------------------------------------------------------------------------------------------+ |
|  | Kỹ Thuật ID | Tên Kỹ Thuật (Technique)      | Chiến Thuật (Tactic)   | Mức Độ Tin Cậy         | |
|  |-------------+-------------------------------+------------------------+------------------------| |
|  | T1055       | Process Injection             | Defense Evasion        | Nghi vấn cao (85%)     | |
|  | T1082       | System Information Discovery  | Discovery              | Đã xác nhận (92%)      | |
|  | T1486       | Data Encrypted for Impact     | Impact                 | Đang theo dõi (70%)    | |
|  +-----------------------------------------------------------------------------------------------+ |
+----------------------------------------------------------------------------------------------------+
|  ĐỀ XUẤT QUY TRÌNH ỨNG PHÓ SỰ CỐ (INCIDENT RESPONSE PLAYBOOK):                                     |
|  [ ] Bước 1: Cách ly máy trạm chứa mã băm e3b0c442 khỏi mạng nội bộ qua cổng Switch/VLAN.          |
|  [ ] Bước 2: Chặn cổng kết nối ra C2 Server tại Firewall biên.                                     |
|  [ ] Bước 3: Thu hồi toàn bộ Kerberos Ticket của tài khoản đăng nhập trên máy đích.                 |
+----------------------------------------------------------------------------------------------------+
```

---

#### P05 — `/history` (BẢNG DỮ LIỆU LỊCH SỬ & LỌC NÂNG CAO)
- **Bố cục chính:** Bảng dữ liệu tương tác đầy đủ, hỗ trợ lọc đa tiêu chí theo dòng và phân trang chuẩn mực.
- **Phân định Tham số Lọc (Server vs Client Filter Invariant):**
  - **Server Query Parameters (gửi trực tiếp tới `GET /v1/analysis`):** `limit`, `offset`, `status`, `decision`, `input_mode`, `demo_mode`.
  - **Client-Side Filtering (lọc tại chỗ trên tập dữ liệu đã tải về):** Ô tìm kiếm nhanh (Search Text theo Job ID / SHA-256), Bộ chọn khoảng thời gian (Date Range Filter: `7 ngày qua`, `30 ngày qua`).

```
+----------------------------------------------------------------------------------------------------+
|  Nhật Ký & Lịch Sử Phân Tích Mã Độc PE (Analysis Jobs History)                                    |
+----------------------------------------------------------------------------------------------------+
|  BỘ LỌC ĐA TIÊU CHÍ (MULTI-CRITERIA FILTERS):                                                      |
|  [Server: Phán quyết [v] ] [Server: Trạng thái [v] ] [Server: Chế độ nạp [v] ] [Server: Demo [v] ] |
|  [Client: Ô tìm kiếm Job ID, SHA-256...                             ] [Client: Khoảng thời gian [v] ] |
+----------------------------------------------------------------------------------------------------+
|  BẢNG DỮ LIỆU CÁC PHIÊN PHÂN TÍCH (ANALYSIS JOBS):                                                 |
|  +-----------------------------------------------------------------------------------------------+ |
|  | Job ID       | Thời Gian Tạo   | Phán Quyết   | Tin Cậy | Mã Băm Bằng Chứng | Chuyên Viên | Thao Tác |
|  |--------------+-----------------+--------------+---------+-------------------+-------------+----------|
|  | #94a20f51... | 15 phút trước   | [QUARANTINE] | 98.7%   | `e3b0c442...` [C] | analyst-01  | [Xem] [v]|
|  | #81bc321a... | 1 giờ trước     | [PASS]       | 99.1%   | `12fa9831...` [C] | analyst-01  | [Xem] [v]|
|  | #7f0029b4... | 3 giờ trước     | [ALERT]      | 74.2%   | `89ab4102...` [C] | analyst-02  | [Xem] [v]|
|  | #6c3104e9... | Hôm qua 18:30   | [QUARANTINE] | 95.0%   | `55de3198...` [C] | analyst-01  | [Xem] [v]|
|  +-----------------------------------------------------------------------------------------------+ |
|  Hiển thị 1 - 20 trong tổng số 1,420 kết quả             [ < Trang Trước ]  [ 1 ] [ 2 ] [ 3 ] [ Sau > ] |
+----------------------------------------------------------------------------------------------------+
```

---

#### P06 & P07 — `/alerts` & `/alerts/{id}` (SOC TRIAGE & WORKFLOW STEPPER)
- **Bố cục P06 (Danh sách Cảnh báo):** 4 thẻ thống kê ở trên cùng theo 4 trạng thái chuẩn (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`), theo sau là bảng danh sách phân cấp theo mức độ nguy hại (`CRITICAL` màu đỏ nổi bật, `HIGH` màu cam).
- **Bố cục P07 (Quy trình Xử lý Cảnh báo):**
  - **Status Stepper Chuẩn mực (Canonical Alert Lifecycle):**
    `[ OPEN ] =====> [ ACKNOWLEDGED ] =====> [ RESOLVED ]  (Hoặc đóng nhanh: [ DISMISSED ])`
  - Giao diện chia 2 cột:
    - *Cột trái:* Thông tin nguồn gốc mã độc liên kết sang `/analysis/{id}` và trạng thái vòng đời.
    - *Cột phải:* Khung soạn thảo Ghi chú điều tra (Markdown Rich Text - `[UI Gap]`) và Nút chuyển trạng thái tương tác (`PATCH /v1/alerts/{id}` với `{"status": str}`).

```
+----------------------------------------------------------------------------------------------------+
|  Trung Tâm Điều Phối Cảnh Báo SOC (Security Alerts Triage) — P06                                   |
+----------------------------------------------------------------------------------------------------+
|  CHỈ SỐ THEO TRANG HIỆN TẠI (CURRENT PAGE METRICS - 20 BẢN GHI/TRANG):                             |
|  [ CRITICAL: 4 ]       [ ACTIVE / OPEN: 8 ]       [ ACKNOWLEDGED: 5 ]       [ RESOLVED: 3 ]        |
|  *(Tổng số cảnh báo toàn hệ thống khớp bộ lọc: 122 — đối soát từ trường `total` của GET /v1/alerts)* |
+----------------------------------------------------------------------------------------------------+
|  BỘ LỌC CẢNH BÁO: [ Mức độ: Tất cả [v] ]  [ Trạng thái: Tất cả [v] ]  [ Ô tìm kiếm... ] [ Lọc ]    |
+----------------------------------------------------------------------------------------------------+
|  DANH SÁCH CẢNH BÁO AN NINH (SECURITY ALERTS):                                                     |
|  +-----------------------------------------------------------------------------------------------+ |
|  | Alert ID   | Job Liên Kết | Mức Độ    | Trạng Thái     | Thời Gian     | Hành Động                | |
|  |------------+--------------+-----------+----------------+---------------+--------------------------| |
|  | #alt-9041  | #94a20f51... | CRITICAL  | [OPEN]         | 10 phút trước | [Chi Tiết] [Acknowledge] | |
|  | #alt-8912  | #7f0029b4... | HIGH      | [ACKNOWLEDGED] | 2 giờ trước   | [Chi Tiết] [Resolve]     | |
|  | #alt-7650  | #6c3104e9... | HIGH      | [RESOLVED]     | Hôm qua       | [Xem Lại]                | |
|  | #alt-7104  | #51aa1209... | MEDIUM    | [DISMISSED]    | 3 ngày trước  | [Xem Lại]                | |
|  +-----------------------------------------------------------------------------------------------+ |
+----------------------------------------------------------------------------------------------------+
```

```
+----------------------------------------------------------------------------------------------------+
|  Chi Tiết Cảnh Báo SOC #alt-9041 — Phân Tích & Điều Phối Xử Lý — P07                                |
+----------------------------------------------------------------------------------------------------+
|  VÒNG ĐỜI CẢNH BÁO (CANONICAL STATUS STEPPER):                                                     |
|  (●) OPEN  ======>  (○) ACKNOWLEDGED  ======>  (○) RESOLVED         [ Đóng nhanh: ( ) DISMISSED ]  |
+----------------------------------------------------------------------------------------------------+
|  THÔNG TIN CẢNH BÁO GỐC (LEFT COL - 55%):    | ĐIỀU TRA & THAO TÁC (RIGHT COL - 45%):               |
|  - Mã cảnh báo: alt-9041                     | [UI Gap] Phân công: [ analyst-01 (Client-only) [v] ] |
|  - Mức độ nguy hại: CRITICAL                 |                                                      |
|  - Phán quyết máy: QUARANTINE (Score: 0.987) | [UI Gap GAP-15] Ghi chú điều tra (In-Memory Draft):   |
|  - Liên kết Job: [ /analysis/94a20f51... ]   | +--------------------------------------------------+ |
|  - Thời gian tạo: 2026-10-16 08:30:15 UTC    | | Mẫu có hành vi tiêm mã độc VirtualAllocEx...    | |
|  - Bằng chứng băm: `994e7f81...` [Sao chép]  | +--------------------------------------------------+ |
|                                              |                                                      |
|  HÀNH ĐỘNG HỢP LỆ VỚI TRẠNG THÁI 'OPEN':     |                                                      |
|  [ Chuyển sang ACKNOWLEDGED ]                | [ Đóng cảnh báo DISMISSED (False Positive) ]         |
|  *(Lưu ý: Backend PATCH chỉ nhận `status`. Trạng thái RESOLVED/DISMISSED là terminal, không thể đổi)*|
|  *(Lý do đóng cảnh báo >=20 ký tự là kiểm thực UX Client-side GAP-15, in-memory state, không lưu DB)* |
+----------------------------------------------------------------------------------------------------+
```

---

#### P08 — `/system/status` (AUTHENTIC TELEMETRY DASHBOARD TỪ `psutil`)
- **BẤT BIẾN KỸ THUẬT BẮT BUỘC:** Toàn bộ thông số CPU, RAM, Process phải phản ánh chính xác dữ liệu từ backend endpoint `/v1/system/telemetry` qua thư viện hệ thống `psutil`. Nghiêm cấm hiển thị số liệu Disk hay dữ liệu giả lập không có trong hợp đồng backend (FIX-05).
- **Phân định Chỉ số Khả dụng Thực tế vs Khoảng trống Giao diện (P08 Availability Invariant):**
  - **Authentic Data (100% từ `GET /v1/system/telemetry`):**
    - Trạng thái hệ thống: `status` (`"ok"` hoặc `"degraded"`).
    - CPU: `utilization_percent`, `logical_cores`, `physical_cores`.
    - Bộ nhớ: `total_bytes`, `available_bytes`, `used_bytes`, `used_percent`.
    - Tiến trình: `pid`, `rss_bytes`, `vms_bytes`, `thread_count`.
  - **Subsystems Health Probes (từ `GET /health` & `GET /ready`):** Trạng thái kết nối SQL Server và Model LightGBM.
  - **Unsupported Backend Widgets (`DESIGN_ONLY` / `BACKEND_GAP`):**
    - Hostname, OS string, Server Uptime.
    - Database Connection Pool count (`18/50 Active`).
    - Concurrency slots indicator (`50 Free`) và Jev AI Queue depth (`4/16 Active`).
    - *Các trường này được gắn nhãn tĩnh `DESIGN_ONLY` trên wireframe và không được bịa đặt telemetry giả lập.*

```
+----------------------------------------------------------------------------------------------------+
|  Giám Sát Hạ Tầng & Sức Khỏe Nút Tác Chiến (Authentic System Telemetry)                            |
|  [DESIGN_ONLY: Host / OS / Uptime] | Engine: v3.0.0 | Status: OK (psutil telemetry)               |
+----------------------------------------------------------------------------------------------------+
|  BỘ ĐO PHẦN CỨNG THỰC TẾ 100% (AUTHENTIC PSUTIL TELEMETRY):                                        |
|                                                                                                    |
|  +-----------------------+  +-----------------------+  +----------------------------------------+  |
|  | CPU USAGE (psutil)    |  | RAM MEMORY (psutil)   |  | PROCESS RUNTIME (BACKEND PID)          |  |
|  |  [====       ] 14.8%  |  |  [========== ] 50.6%  |  | PID: 14220 | Threads: 12               |  |
|  | Cores: 8L / 4P        |  | 8.4 GB / 17.1 GB Free |  | RSS: 209.8 MB | VMS: 623.9 MB          |  |
|  +-----------------------+  +-----------------------+  +----------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
|  TÌNH TRẠNG PHÂN HỆ CỐT LÕI (PROBES & SUBSYSTEMS STATUS):                                          |
|                                                                                                    |
|  [OK] SQL Server 2022 Database: READY (từ /ready; Pool details: DESIGN_ONLY)                       |
|  [OK] ML Detector Ensemble: READY (từ /ready; Concurrency slots: DESIGN_ONLY)                      |
|  [WARN] Jev AI Advisory (LM Studio): DEGRADED (từ /health; Queue depth: DESIGN_ONLY)              |
+----------------------------------------------------------------------------------------------------+
|  Truy vấn trực tiếp Prometheus: [ Mở Endpoint /metrics ] | Cập nhật tự động mỗi 10 giây             |
+----------------------------------------------------------------------------------------------------+
```

---

#### P09 & P10 — `/evaluation` & `/auth/switch` (BENCHMARK & DEV SWITCHER)
- **P09 — Benchmark Mô hình [DESIGN_ONLY / BACKEND_GAP]:** Bảng điểm 4 chỉ số (Accuracy, F1, FPR, AUC) và Ma trận nhầm lẫn 2x2 thể hiện rõ số lượng phát hiện True Positive, True Negative, False Positive, False Negative. Backend hiện vận hành benchmark qua offline CLI runner ghi vào `experiment_runs`, chưa có HTTP endpoint `/v1/evaluate`.
- **P10 — Chuyển đổi Danh tính Dev:**
  - 5 Thẻ Chuyển Vai trò Nhanh: `Admin`, `Lead Analyst`, `Secondary Analyst`, `Operator`, `Evaluator`.
  - Nhấp chuột 1-Click tự động thay thế Bearer token trong `localStorage` và cập nhật Axios HTTP Interceptor ngay lập tức mà không cần đăng nhập lại.

---

### 4. TRẠNG THÁI TẢI, LỖI & PHẢN HỒI VI TƯƠNG TÁC (LOADING, ERROR & INTERACTION STATES)

#### 4.1. Bộ Khung Tải Trạng Thái Xương Cá (Skeleton Loading Invariant)
> [!IMPORTANT]
> **CẤM TUYỆT ĐỐI** sử dụng Spinner tròn quay ở giữa màn hình trắng gây mất phương hướng thị giác. Toàn bộ các trang khi chờ dữ liệu API đều bắt buộc hiển thị Skeleton Loading mô phỏng chính xác 100% hình thái của nội dung sắp xuất hiện (Thanh Hero, Hàng trong bảng, Thẻ chỉ số).

- **Hiệu ứng Shimmer mượt mà:** Khối nền `#20252d` chuyển sắc nhẹ nhàng sang `#29303b` với chu kỳ 1.5 giây.
- **Bảo toàn chiều cao (Layout Shift Prevention):** Mọi khung Skeleton đều được cấp thuộc tính chiều cao tối thiểu (`min-h-[...]`) khớp với chiều cao render thực tế của dữ liệu nhằm đạt chỉ số **CLS (Cumulative Layout Shift) = 0.00**.

#### 4.2. Báo Lỗi Cục Bộ Ngay Dưới Trường Dữ Liệu (Inline Field Error Invariant)
- Khi dữ liệu không hợp lệ:
  - Viền ô nhập liệu chuyển sang màu đỏ cảnh báo (`--color-verdict-malicious`).
  - Biểu tượng cảnh báo hình tròn kèm dấu chấm than xuất hiện ở góc phải của input.
  - Dòng thông báo lỗi hiển thị ngay bên dưới với cỡ chữ $13\text{px}$ màu đỏ dịu, giải thích chính xác tiêu chí chưa đạt (ví dụ: `Số thực phải nằm trong khoảng từ 0.0 đến 1.0`).

#### 4.3. Hộp Thoại Hành Động Nguy Hiểm (Destructive Action Confirmation Modal)
- Áp dụng khi Chuyên viên SOC bấm **"Đóng Cảnh Báo (False Positive)"** hoặc **"Xóa Dữ Liệu Phân Tích"**:
  - Modal xuất hiện ở trung tâm kèm hiệu ứng mờ nền Backdrop Blur ($8\text{px}$).
  - Tiêu đề modal hiển thị màu đỏ cảnh báo: `Xác Nhận Đóng Cảnh Báo Nguy Hiểm`.
  - Bắt buộc nhập văn bản lý do tối thiểu 20 ký tự để kích hoạt nút Primary CTA "Xác Nhận Đóng".
  - Nút Hủy bỏ (Secondary) nằm bên trái, nút Xác nhận Nguy hiểm (Primary Danger) nằm bên phải với nhãn hành động cụ thể: `Đóng Cảnh Báo / Giữ Lại Theo Dõi` (Tuân thủ nghiêm ngặt **Jakob's Law**, cấm dùng `Yes/No` hoặc `OK/Cancel`).
