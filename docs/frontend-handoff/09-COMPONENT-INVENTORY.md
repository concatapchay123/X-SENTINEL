# 09 — DANH MỤC THÀNH PHẦN GIAO DIỆN TÁI SỬ DỤNG (COMPONENT INVENTORY)
## HỆ THỐNG X-SENTINEL V3 — MALWARE ANALYSIS & THREAT DETECTION PLATFORM

---

### MỤC LỤC
1. [Tổng Quan Kiến Trúc Thành Phần Frontend (Atomic Design Hierarchy)](#1-tổng-quan-kiến-trúc-thành-phần-frontend-atomic-design-hierarchy)
2. [Bảng Phân Bổ 35 Thành Phần Theo 7 Danh Mục Nghiệp Vụ](#2-bảng-phân-bổ-35-thành-phần-theo-7-danh-mục-nghiệp-vụ)
3. [Đặc Tả Chi Tiết 35 Thành Phần (Component Specifications)](#3-đặc-tả-chi-tiết-35-thành-phần-component-specifications)
   - [Nhóm 1: Base UI Elements (C01 - C08)](#nhóm-1-base-ui-elements-c01---c08)
   - [Nhóm 2: Data Display & Metrics (C09 - C15)](#nhóm-2-data-display--metrics-c09---c15)
   - [Nhóm 3: Visualizations & Charts (C16 - C20)](#nhóm-3-visualizations--charts-c16---c20)
   - [Nhóm 4: Complex Domain Components (C21 - C25)](#nhóm-4-complex-domain-components-c21---c25)
   - [Nhóm 5: Workflow & SOC Triage (C26 - C29)](#nhóm-5-workflow--soc-triage-c26---c29)
   - [Nhóm 6: Tables, Filters & Navigation (C30 - C35)](#nhóm-6-tables-filters--navigation-c30---c35)
4. [Nguyên Tắc Accessibility (a11y) & Hướng Dẫn Tích Hợp Tailwind](#4-nguyên-tắc-accessibility-a11y--hướng-dẫn-tích-hợp-tailwind)

---

### 1. TỔNG QUAN KIẾN TRÚC THÀNH PHẦN FRONTEND (ATOMIC DESIGN HIERARCHY)

Tất cả các thành phần giao diện của X-SENTINEL V3 được cấu trúc theo hệ thống phân cấp chặt chẽ trong thư mục `src/components/`, đảm bảo tính đóng gói (encapsulation), khả năng kiểm thử độc lập (isolated testability) và tái sử dụng tối đa:

```
src/components/
├── ui/              # Nguyên tử (Atoms): Button, Input, Badge, Tooltip, Dialog
├── metrics/         # Phân tử Số liệu: HeroVerdictCard, RadialConfidenceGauge, EvidenceHashBlock
├── visualizations/  # Đồ thị & Trực quan: ShapWaterfallChart, ConfusionMatrixHeatmap, TelemetryGauge
├── domain/          # Thành phần Nghiệp vụ Chuyên sâu: FeatureVectorEditor, JevAdvisoryContainer, MitreAttackMatrix
├── workflow/        # Quy trình Tác chiến SOC: AlertStatusStepper, InvestigationNoteEditor
├── tables/          # Bảng Dữ liệu & Lọc: DataTable, FilterToolbar, PaginationControls
└── feedback/        # Phản hồi & Khung trạng thái: SkeletonCard, InlineFieldError, Toast, EmptyState
```

---

### 2. BẢNG PHÂN BỔ 35 THÀNH PHẦN THEO 7 DANH MỤC NGHIỆP VỤ

| Mã C | Tên Thành Phần (Component Name) | Đường Dẫn Tệp Nguồn | Mục Đích Tái Sử Dụng | Mức Độ Phức Tạp |
|:---|:---|:---|:---|:---|
| **C01** | `Button` | `src/components/ui/button.tsx` | Nút bấm tiêu chuẩn với tỷ lệ 2:1 và biến thể hành động | Thấp (Atom) |
| **C02** | `Input` | `src/components/ui/input.tsx` | Ô nhập liệu văn bản với nhãn và viền trạng thái | Thấp (Atom) |
| **C03** | `Select` | `src/components/ui/select.tsx` | Menu thả chọn giá trị đơn lẻ hỗ trợ tìm kiếm | Trung bình |
| **C04** | `Checkbox` | `src/components/ui/checkbox.tsx` | Hộp kiểm vuông với trạng thái xác thực rõ ràng | Thấp (Atom) |
| **C05** | `RadioGroup` | `src/components/ui/radio-group.tsx` | Nhóm nút radio tròn cho 1 lựa chọn duy nhất | Thấp (Atom) |
| **C06** | `Badge` | `src/components/ui/badge.tsx` | Huy hiệu phán quyết, trạng thái job, mức nghiêm trọng | Thấp (Atom) |
| **C07** | `Tooltip` | `src/components/ui/tooltip.tsx` | Chú giải kỹ thuật khi hover vào các chỉ số phức tạp | Thấp (Atom) |
| **C08** | `Dialog` (Modal) | `src/components/ui/dialog.tsx` | Hộp thoại xác nhận, popup chi tiết và cảnh báo | Trung bình |
| **C09** | `HeroVerdictCard` | `src/components/metrics/hero-verdict-card.tsx` | Thẻ tiêu điểm thị giác độc tôn hiển thị Phán quyết | Cao (Organism) |
| **C10** | `RadialConfidenceGauge` | `src/components/metrics/radial-confidence-gauge.tsx` | Đồng hồ tròn hiển thị tỷ lệ % tin cậy | Trung bình |
| **C11** | `MetricCard` | `src/components/metrics/metric-card.tsx` | Thẻ tóm tắt chỉ số KPI (Alerts, Health, Accuracy) | Trung bình |
| **C12** | `EvidenceHashBlock` | `src/components/metrics/evidence-hash-block.tsx` | Khối mật mã SHA-256 kèm nút copy 1-click | Trung bình |
| **C13** | `ModuleScoreRow` | `src/components/metrics/module-score-row.tsx` | Dòng hiển thị điểm và tỷ lệ đóng góp của M1-M5 | Trung bình |
| **C14** | `JsonViewer` | `src/components/metrics/json-viewer.tsx` | Trình duyệt cây JSON có tô màu cú pháp và tìm kiếm | Cao |
| **C15** | `StatusPill` | `src/components/metrics/status-pill.tsx` | Đèn chỉ báo trạng thái realtime nhấp nháy | Thấp (Atom) |
| **C16** | `ShapWaterfallChart` | `src/components/visualizations/shap-waterfall.tsx` | Biểu đồ thanh ngang thể hiện giá trị SHAP đóng góp | Rất cao |
| **C17** | `TopFeaturesBarChart` | `src/components/visualizations/top-features-bar.tsx` | Biểu đồ Top 15 đặc trưng ảnh hưởng nhiều nhất | Cao |
| **C18** | `ConfusionMatrixHeatmap` | `src/components/visualizations/confusion-matrix.tsx` | Lưới nhiệt 2x2 ma trận nhầm lẫn benchmark | Cao |
| **C19** | `TelemetryGauge` | `src/components/visualizations/telemetry-gauge.tsx` | Đồng hồ đo CPU, RAM, Process từ dữ liệu `psutil` | Trung bình |
| **C20** | `TimelineEvent` | `src/components/visualizations/timeline-event.tsx` | Mốc thời gian trên dòng sự kiện điều tra cảnh báo | Trung bình |
| **C21** | `FeatureVectorEditor` | `src/components/domain/feature-vector-editor.tsx` | Trình soạn thảo và xác thực vector 2.381 chiều | Rất cao |
| **C22** | `SamplePresetLoader` | `src/components/domain/sample-preset-loader.tsx` | Bộ nạp dữ liệu mẫu benchmark 1-click | Trung bình |
| **C23** | `MitreAttackMatrixTable` | `src/components/domain/mitre-attack-matrix.tsx` | Bảng ma trận chiến thuật ATT&CK có phân cấp | Cao |
| **C24** | `PlaybookStepList` | `src/components/domain/playbook-step-list.tsx` | Danh sách checklist ứng phó sự cố có thể đánh dấu | Trung bình |
| **C25** | `JevAdvisoryContainer` | `src/components/domain/jev-advisory-container.tsx` | Khung cố vấn Jev AI bắt buộc có Banner cảnh báo | Cao |
| **C26** | `AlertStatusStepper` | `src/components/workflow/alert-status-stepper.tsx` | Thanh quy trình 4 bước chuyển trạng thái cảnh báo | Cao |
| **C27** | `InvestigationNoteEditor`| `src/components/workflow/investigation-note-editor.tsx`| [UI Gap] Soạn thảo ghi chú điều tra (Lưu client-side) | Cao |
| **C28** | `DangerousActionModal` | `src/components/workflow/dangerous-action-modal.tsx` | Hộp thoại yêu cầu lý do khi đóng cảnh báo | Cao |
| **C29** | `AssignmentSelector` | `src/components/workflow/assignment-selector.tsx` | [UI Gap] Dropdown phân công điều tra viên (Client-side)| Trung bình |
| **C30** | `DataTable` | `src/components/tables/data-table.tsx` | Bảng dữ liệu đa năng với sort, filter, responsive | Rất cao |
| **C31** | `MultiCriteriaFilterToolbar` | `src/components/tables/filter-toolbar.tsx` | Thanh công cụ lọc đa chiều (trạng thái, ngày) | Cao |
| **C32** | `PaginationControls` | `src/components/tables/pagination-controls.tsx` | Bộ điều hướng trang hiển thị tổng số và nhảy trang | Trung bình |
| **C33** | `BreadcrumbNav` | `src/components/navigation/breadcrumb-nav.tsx` | Thanh đường dẫn phân cấp điều hướng nhanh | Thấp |
| **C34** | `SidebarNav` | `src/components/navigation/sidebar-nav.tsx` | Thanh điều hướng bên hông có phân quyền vai trò | Cao |
| **C35** | `RoleProfileBadge` | `src/components/navigation/role-profile-badge.tsx` | Thẻ hiển thị vai trò hiện tại và nút switch dev | Trung bình |

---

### 3. ĐẶC TẢ CHI TIẾT 35 THÀNH PHẦN (COMPONENT SPECIFICATIONS)

#### NHÓM 1: BASE UI ELEMENTS (C01 - C08)

##### C01 — `Button`
- **File:** `src/components/ui/button.tsx`
- **Props Interface:**
  ```typescript
  export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    isLoading?: boolean;
    leftIcon?: React.ReactNode;
    rightIcon?: React.ReactNode;
  }
  ```
- **Quy tắc Impeccable:**
  - Tỷ lệ đệm $Padding_X = 2 \times Padding_Y$ (`size='md'`: `py-2.5 px-5`, `size='lg'`: `py-3.5 px-7`).
  - Nhãn nút viết Title Case hành động cụ thể, cấm ALL CAPS.
  - Khi `isLoading: true`, ẩn nhãn và thay bằng SVG spinner đồng màu, giữ nguyên kích thước để không gây nhảy layout.
  - Variant `danger` sử dụng màu đỏ cảnh báo `--color-verdict-malicious` cho hành động không thể hoàn tác.

##### C02 — `Input`
- **File:** `src/components/ui/input.tsx`
- **Props Interface:**
  ```typescript
  export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label: string;
    helperText?: string;
    errorMessage?: string;
    isOptional?: boolean;
    startAdornment?: React.ReactNode;
    endAdornment?: React.ReactNode;
  }
  ```
- **Quy tắc Impeccable:**
  - Phân tầng tam cấp: Nhãn in đậm bên trên ($14\text{px}$, `--color-text-primary`) -> Ô nhập liệu nền `--color-bg-subtle` ($15\text{px}$) -> Dòng hướng dẫn hoặc lỗi bên dưới.
  - Khoảng cách từ Label đến Input cố định chính xác $12\text{px}$.
  - Nếu `errorMessage` có giá trị, viền ô nhập đổi thành màu đỏ và hiển thị icon cảnh báo.

##### C06 — `Badge`
- **File:** `src/components/ui/badge.tsx`
- **Props Interface:**
  ```typescript
  export interface BadgeProps {
    variant: 'malicious' | 'suspicious' | 'benign' | 'critical' | 'high' | 'medium' | 'low' | 'neutral';
    label: string;
    size?: 'sm' | 'md';
    hasDotPulse?: boolean;
  }
  ```
- **Hành vi hiển thị:** Nền mờ trong suốt $15\%$ kết hợp với viền mỏng cùng màu độ tương phản cao, phông chữ Mono hoặc Sans in hoa nhẹ nhàng (`font-semibold tracking-wide text-xs`).

##### C08 — `Dialog` (Modal)
- **File:** `src/components/ui/dialog.tsx`
- **Props Interface:**
  ```typescript
  export interface DialogProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    description?: string;
    children: React.ReactNode;
    footer?: React.ReactNode;
    maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
  }
  ```
- **Quy tắc Accessibility:** Bắt buộc có nút đóng [X] ở góc trên bên phải, hỗ trợ đóng nhanh khi bấm phím `Escape`, tự động khóa con trỏ tiêu điểm (Focus Trap) bên trong modal khi mở.

---

#### NHÓM 2: DATA DISPLAY & METRICS (C09 - C15)

##### C09 — `HeroVerdictCard` (Thẻ Tiêu Điểm Phán Quyết Độc Tôn)
- **File:** `src/components/metrics/hero-verdict-card.tsx`
- **Mục đích:** Là thành phần trực quan quan trọng nhất của hệ thống, thể hiện kết luận phân loại của mô hình AI đối với mẫu mã độc.
- **Props Interface:**
  ```typescript
  import { DecisionVerdict } from '@/types/enums';

  export interface HeroVerdictCardProps {
    verdict: DecisionVerdict; // 'PASS' | 'ALERT' | 'QUARANTINE' | 'DEMO_ONLY'
    confidenceScore: number; // 0.0 - 1.0 (malware_score hoặc suspicion_score)
    candidateVerdict?: string; // Dùng khi demo_mode=True để hiển thị phán quyết toán học ứng viên
    inferenceLatencyMs: number;
    analyzedAt: string;
    jobId: string;
  }
  ```
- **Thiết kế Trực quan:**
  - `QUARANTINE`: Nền chuyển sắc sâu từ `--color-bg-surface` sang viền đỏ rực rỡ (`--color-danger`), biểu tượng khiên vỡ cảnh báo mẫu mã độc cực kỳ nguy hiểm.
  - `ALERT`: Viền màu hổ phách (`--color-warning`), biểu tượng dấu chấm than tam giác cảnh báo mẫu nghi ngờ vượt ngưỡng.
  - `PASS`: Viền màu xanh ngọc lục bảo (`--color-success`), biểu tượng khiên bảo vệ toàn vẹn xác nhận mẫu phần mềm lành tính.
  - `DEMO_ONLY`: Viền màu tím / xanh lam cảnh báo chế độ thử nghiệm synthetic (không áp dụng trong pháp chứng chính thức).

##### C12 — `EvidenceHashBlock` (Khối Mật Mã SHA-256)
- **File:** `src/components/metrics/evidence-hash-block.tsx`
- **Props Interface:**
  ```typescript
  export interface EvidenceHashBlockProps {
    evidenceHash: string; // Chuỗi 64 ký tự Hex SHA-256
    algorithm?: string;  // Mặc định 'SHA-256 (HMAC Guarded)'
    onExportJson?: () => void;
  }
  ```
- **Hành vi:** Hiển thị mã băm trong khối phông chữ monospace (`font-mono text-sm tracking-wider`), tự động ngắt dòng thông minh, có nút "Sao Chép" kèm hiệu ứng đổi sang icon tích xanh "Đã chép" trong 2 giây.

---

#### NHÓM 3: VISUALIZATIONS & CHARTS (C16 - C20)

##### C16 — `ShapWaterfallChart` (Biểu Đồ Giải Trình SHAP) [STATUS: DESIGN_ONLY / BACKEND_GAP]
- **File:** `src/components/visualizations/shap-waterfall.tsx`
- **Lưu ý Khả dụng Dữ liệu:** Do Backend `GET /v1/analysis/{id}` hiện tại chỉ trả về `view_contributions` (3 Semantic Views) và chẩn đoán `scores` (M1–M5), chưa có endpoint bóc tách mảng 2.381 giá trị SHAP cá nhân (`GAP-14`), component này hoạt động dựa trên dữ liệu mẫu minh họa (Mock Data) / Design Only cho tới khi Backend mở rộng API XAI.
- **Props Interface:**
  ```typescript
  export interface ShapWaterfallChartProps {
    baseValue: number; // E[f(x)] ví dụ: 0.12
    outputValue: number; // f(x) ví dụ: 0.987
    features: Array<{
      name: string;
      value: number;
      shapValue: number; // Trọng số đóng góp âm hoặc dương
    }>;
    maxDisplayCount?: number; // Mặc định 15 đặc trưng lớn nhất
    isMockData?: boolean; // Luôn hiển thị badge cảnh báo Mock Data
  }
  ```
- **Thiết kế Đồ họa:** Dựng trên thư viện Recharts hoặc ECharts, thanh ngang màu đỏ cam cho SHAP dương (tăng nguy cơ độc hại), thanh ngang màu xanh ngọc cho SHAP âm (giảm nguy cơ).

##### C17 — `TopFeaturesBarChart` (Biểu Đồ Top 15 Đặc Trưng SHAP) [STATUS: DESIGN_ONLY / BACKEND_GAP]
- **File:** `src/components/visualizations/top-features-bar.tsx`
- **Mục đích:** Xếp hạng trực quan 15 đặc trưng có trọng số SHAP tuyệt đối cao nhất. Cùng phụ thuộc vào Mock Data tương tự C16 cho đến khi có API Backend (`GAP-14`).

##### C19 — `TelemetryGauge` (Đồng Hồ Viễn Trắc Phần Cứng `psutil`)
- **File:** `src/components/visualizations/telemetry-gauge.tsx`
- **Mục đích:** Trực quan hóa dữ liệu đo lường phần cứng thực tế 100% từ `psutil` qua API `GET /v1/system/telemetry` (`AuthenticTelemetryResponse`).
- **Props Interface:**
  ```typescript
  export interface TelemetryGaugeProps {
    title: string;
    percentage: number; // 0 - 100 (từ cpu.utilization_percent hoặc memory.used_percent)
    usedDisplay: string; // ví dụ: '8.4 GB' hoặc 'PID 14220'
    totalDisplay?: string; // ví dụ: '17.1 GB' (Memory) hoặc '8 Cores' (CPU)
    status: 'healthy' | 'warning' | 'critical'; // tính từ ngưỡng: <70% healthy, 70-85% warning, >85% critical
    detailText?: string; // ví dụ: 'Threads: 12 | RSS: 209.8 MB'
  }
  ```
- **Ánh xạ từ DTO Backend:**
  - *CPU Gauge:* `percentage = telemetry.cpu.utilization_percent`, `usedDisplay = `${telemetry.cpu.utilization_percent}%``, `totalDisplay = `${telemetry.cpu.logical_cores ?? '?'} Cores``.
  - *RAM Gauge:* `percentage = telemetry.memory.used_percent`, `usedDisplay = formatBytes(telemetry.memory.used_bytes)`, `totalDisplay = formatBytes(telemetry.memory.total_bytes)`.
  - *Process Gauge:* `percentage = (telemetry.process.rss_bytes / telemetry.memory.total_bytes) * 100`, `usedDisplay = formatBytes(telemetry.process.rss_bytes)`, `detailText = `PID: ${telemetry.process.pid} | Threads: ${telemetry.process.thread_count}``.
- **Màu sắc động:** Chuyển từ xanh lá ($< 70\%$) sang hổ phách ($70 - 85\%$) và đỏ cảnh báo ($> 85\%$).

---

#### NHÓM 4: COMPLEX DOMAIN COMPONENTS (C21 - C25)

##### C21 — `FeatureVectorEditor` (Trình Soạn Thảo Vector 2.381 Chiều)
- **File:** `src/components/domain/feature-vector-editor.tsx`
- **Props Interface:**
  ```typescript
  export interface FeatureVectorEditorProps {
    value: number[];
    onChange: (vectors: number[]) => void;
    onValidate?: (isValid: boolean) => void;
  }
  ```
- **Tính năng cao cấp:**
  - Hỗ trợ dán trực tiếp chuỗi JSON hoặc mảng ngăn cách bởi dấu phẩy.
  - Tự động đếm số lượng phần tử theo thời gian thực ($Current/2.381$).
  - Thanh tiến trình mini hiển thị màu xanh khi chạm mốc 2.381 phần tử hợp lệ.

##### C25 — `JevAdvisoryContainer` (Khung Khuyến Nghị Jev AI)
- **File:** `src/components/domain/jev-advisory-container.tsx`
- **BẤT BIẾN BẮT BUỘC:** Thành phần này luôn có viền vàng hổ phách và thanh tiêu đề cảnh báo cố định:
  ```tsx
  <div className="rounded-xl border-2 border-amber-500/40 bg-amber-950/10 p-6">
    <div className="flex items-center gap-3 border-b border-amber-500/20 pb-4 mb-4">
      <AlertTriangle className="h-6 w-6 text-amber-400" />
      <div>
        <h3 className="text-base font-bold text-amber-200">
          KHUYẾN NGHỊ THAM KHẢO DUY NHẤT (ADVISORY ONLY)
        </h3>
        <p className="text-xs text-amber-300/80">
          Nội dung do Jev AI tổng hợp tự động. Không thay thế cho Canonical Evidence.
        </p>
      </div>
    </div>
    {children}
  </div>
  ```

---

#### NHÓM 5: WORKFLOW & SOC TRIAGE (C26 - C29)

##### C26 — `AlertStatusStepper` (Thanh Quy Trình Trạng Thái Cảnh Báo)
- **File:** `src/components/workflow/alert-status-stepper.tsx`
- **Props Interface:**
  ```typescript
  export type AlertLifecycleStatus = 'open' | 'acknowledged' | 'resolved' | 'dismissed';

  export interface AlertStatusStepperProps {
    currentStatus: AlertLifecycleStatus;
    onStatusChange: (nextStatus: AlertLifecycleStatus) => void;
    canUpdate: boolean; // Chỉ bật khi có quyền ALERT_UPDATE
  }
  ```
- **Hành vi:** Hiển thị các bước tiến trình chuẩn mực: `open` -> `acknowledged` -> `resolved` (hoặc đóng nhanh với `dismissed`). Người dùng nhấp chuột vào nấc kế tiếp để kích hoạt thay đổi trạng thái kèm xác nhận.

##### C27 — `InvestigationNoteEditor` (Khung Soạn Thảo Ghi Chú Điều Tra) [UI GAP]
- **File:** `src/components/workflow/investigation-note-editor.tsx`
- **Đặc tả & Khoảng trống Kỹ thuật:** Cung cấp trình soạn thảo Markdown cho phép chuyên viên điều tra nhập ghi chú xử lý sự cố.
- **Lưu ý UI Gap:** Backend API `PATCH /v1/alerts/{id}` hiện tại chỉ chấp nhận `{ status: str }` và không lưu trữ `investigation_notes` trong CSDL. Do đó, ghi chú được duy trì trong Client In-Memory State (React/Zustand) phục vụ phiên làm việc của điều tra viên (`GAP-15`). Nghiêm cấm lưu vào unencrypted localStorage vì rủi ro an ninh dữ liệu SOC.

##### C28 — `DangerousActionModal` (Hộp Thoại Xác Nhận Đóng Cảnh Báo)
- **File:** `src/components/workflow/dangerous-action-modal.tsx`
- **Yêu cầu Bắt buộc:** Bắt buộc nhập trường `investigation_notes` tối thiểu 20 ký tự giải trình lý do (kiểm thực client-side) trước khi nút "Xác Nhận Đóng Cảnh Báo" chuyển sang trạng thái khả dụng để gửi lệnh `PATCH /v1/alerts/{id}` với `status: 'dismissed'`.

##### C29 — `AssignmentSelector` (Dropdown Phân Công Chuyên Viên) [UI GAP]
- **File:** `src/components/workflow/assignment-selector.tsx`
- **Đặc tả & Khoảng trống Kỹ thuật:** Dropdown cho phép chọn chuyên viên thụ lý cảnh báo.
- **Lưu ý UI Gap:** Backend `alerts` table không có cột `assignee_id`. Việc phân công chuyên viên chỉ lưu tại tầng Client State phục vụ hiển thị trên bảng SOC.

---

#### NHÓM 6: TABLES, FILTERS & NAVIGATION (C30 - C35)

##### C30 — `DataTable` (Bảng Dữ Liệu Tác Chiến Đa Năng)
- **File:** `src/components/tables/data-table.tsx`
- **Props Interface:**
  ```typescript
  export interface ColumnDef<T> {
    header: string;
    accessorKey: keyof T | string;
    cell?: (item: T) => React.ReactNode;
    sortable?: boolean;
    width?: string;
  }

  export interface DataTableProps<T> {
    columns: ColumnDef<T>[];
    data: T[];
    isLoading?: boolean;
    emptyMessage?: string;
    onRowClick?: (item: T) => void;
  }
  ```
- **Quy tắc Thiết kế:** Bố cục phẳng, cấm kẻ viền ngang dọc đậm đặc cơ học, khoảng cách dòng thoáng đãng ($Padding_Y = 14\text{px}$), hiệu ứng hover đổi màu nền bề mặt nhẹ nhàng.

---

### 4. NGUYÊN TẮC ACCESSIBILITY (a11y) & HƯỚNG DẪN TÍCH HỢP TAILWIND

1. **Điều Hướng Hoàn Toàn Bằng Bàn Phím (Keyboard Navigation):**
   - Mọi nút bấm, ô input, dropdown và hàng trong bảng đều có đường viền chỉ báo tiêu điểm rõ ràng (`focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:outline-none`).
2. **Hỗ Trợ Trình Đọc Màn Hình (Screen Readers / ARIA):**
   - Các biểu đồ phức tạp (C16, C18) bắt buộc đi kèm thuộc tính `aria-label` mô tả tóm tắt kết quả (ví dụ: `aria-label="Biểu đồ giải trình SHAP: Đặc trưng Entropy section text đóng góp cao nhất"`).
3. **Chống Chói Mắt & Trực Quan Hóa Tối Ưu (Tailwind Best Practices):**
   - Áp dụng triệt để các biến lớp CSS chuẩn hóa trong `tailwind.config.js` đã được mapping với Design Tokens tại Mục 1.1, cấm hardcode mã màu Hex rời rạc trong component.
