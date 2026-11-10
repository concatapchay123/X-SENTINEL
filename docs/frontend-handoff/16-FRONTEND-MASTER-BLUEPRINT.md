# 16 — BẢN THIẾT KẾ MẪU TOÀN NĂNG DÀNH CHO AI AGENT (FRONTEND MASTER BLUEPRINT)
## HỆ THỐNG X-SENTINEL V3 — MALWARE ANALYSIS & THREAT DETECTION PLATFORM

---

### MỤC LỤC
1. [Chỉ Lệnh Tối Cao Dành Cho AI Coding Agent (Executive Architecture Mandate)](#1-chỉ-lệnh-tối-cao-dành-cho-ai-coding-agent-executive-architecture-mandate)
2. [Cấu Trúc Thư Mục Chuẩn Mực Next.js 14+ (Project Scaffold)](#2-cấu-trúc-thư-mục-chuẩn-mực-nextjs-14-project-scaffold)
3. [Tệp Cấu Hình Khởi Động Thiết Yếu (`package.json`, `tailwind.config.js`)](#3-tệp-cấu-hình-khởi-động-thiết-yếu-packagejson-tailwindconfigjs)
4. [Cẩm Nang 5 Giai Đoạn Triển Khai Tự Hành (Autonomous Execution Guide)](#4-cẩm-nang-5-giai-đoạn-triển-khai-tự-hành-autonomous-execution-guide)
5. [Bộ Quy Tắc Vàng & Tiêu Chuẩn Nghiệm Thu Tuyệt Đối (Golden Invariants)](#5-bộ-quy-tắc-vàng--tiêu-chuẩn-nghiệm-thu-tuyệt-đối-golden-invariants)
6. [Bản Đồ Điều Hướng Bộ Tài Liệu Kỹ Thuật (Documentation Map 00 - 15)](#6-bản-đồ-điều-hướng-bộ-tài-liệu-kỹ-thuật-documentation-map-00---15)

---

### 1. CHỈ LỆNH TỐI CAO DÀNH CHO AI CODING AGENT (EXECUTIVE ARCHITECTURE MANDATE)

> [!IMPORTANT]
> **DÀNH CHO AI FRONTEND CODING AGENT HOẶC SENIOR FRONTEND DEVELOPER TIẾP QUẢN DỰ ÁN:**
> Khi nhận nhiệm vụ xây dựng giao diện Frontend cho hệ thống **X-SENTINEL V3**, bạn **BẮT BUỘC TUÂN THỦ TUYỆT ĐỐI** các nguyên tắc bất biến sau:

1. **Bất Biến Pure Headless REST API:** Backend của hệ thống là một nền tảng Headless REST API thuần túy trả về định dạng JSON chuẩn hóa. **NGHIÊM CẤM TUYỆT ĐỐI** việc tạo mới, sửa đổi hoặc khôi phục các tệp Jinja Template (`*.html`), static CSS/JS dư thừa, hoặc thư mục giả lập (`frontend-preview/`) trong phần Backend.
2. **Luật Bất Xâm Phạm Mã Nguồn Backend (Zero Backend Tampering):** Không được sửa đổi bất kỳ tệp mã nguồn Python nào trong `backend/src/x_sentinel/`, không sửa cấu hình cơ sở dữ liệu, không chạy migration sửa schema SQL Server. Toàn bộ mã nguồn Frontend mới phải nằm độc lập trong thư mục `frontend/` (hoặc `frontend-next/`).
3. **Bất Biến Phân Tách Chứng Cứ Canonical vs Khuyến Nghị Jev AI:**
   - Kết quả suy luận từ bộ 5 Module Detector M1-M5 (M1: TADR, M2: Tabular STRIP, M3: View Concentration, M4: Cross-View Disagreement, M5: Semantic Plausibility) kết hợp với Mã Băm Bằng Chứng SHA-256 (`evidence_hash`) là **Bằng Chứng Chuẩn Mực (Canonical Evidence) — Căn cứ kỹ thuật và pháp lý duy nhất**. Phải được hiển thị tại Hero Verdict Card trên trang `/analysis/{id}`.
   - Nhận định tự nhiên từ Jev AI mang cờ `advisory_only: true` là **Khuyến nghị tham khảo duy nhất**. **BẮT BUỘC** hiển thị trong khung viền hổ phách độc lập kèm Banner cảnh báo: `[KHUYẾN NGHỊ THAM KHẢO DUY NHẤT] Không có giá trị pháp lý thay thế Canonical Evidence`.
4. **An Toàn Kiểu Đóng (Fail-Closed) Cho Tệp PE Thô:** Endpoint `POST /v1/analyze/file` trả về HTTP 501 `XS_FEATURE_DISABLED`. Frontend phải khóa tính năng nộp file thô kèm huy hiệu cảnh báo an ninh, hướng dẫn người dùng nộp Feature Vector 2.381 chiều.
5. **Viễn Trắc Phần Cứng Chân Thực (Authentic Telemetry):** Thông số CPU, RAM, Process hiển thị tại `/system/status` bắt buộc lấy từ dữ liệu thực tế của thư viện `psutil` qua endpoint `/v1/system/telemetry`. Cấm dùng dữ liệu ngẫu nhiên hoặc giả lập.
6. **Bảo Vệ Quyền Sở Hữu Dữ Liệu BOLA/IDOR:** Bắt chặn mã lỗi HTTP 403 `XS_FORBIDDEN` và hiển thị màn hình rào chắn an ninh `BOLAErrorView`, không làm sập ứng dụng (Zero Crash).

---

### 2. CẤU TRÚC THƯ MỤC CHUẨN MỰC NEXT.JS 14+ (PROJECT SCAFFOLD)

Toàn bộ ứng dụng Frontend được tổ chức theo kiến trúc Next.js App Router chuẩn mực:

```
frontend/
├── src/
│   ├── app/                                 # Các tuyến đường giao diện (10 trang chính thức)
│   │   ├── layout.tsx                       # Master Root Layout (Sidebar + Header + Providers)
│   │   ├── globals.css                      # Global styles & Tailwind Directives
│   │   ├── page.tsx                         # Redirect sang /analyze hoặc /history
│   │   ├── analyze/
│   │   │   └── page.tsx                     # P01: Nộp mẫu phân tích PE (2,381-Dim Vector)
│   │   ├── analysis/
│   │   │   └── [id]/
│   │   │       ├── page.tsx                 # P02: Chi tiết Canonical Evidence & Hero Verdict
│   │   │       ├── explainability/
│   │   │       │   └── page.tsx             # P03: Giải trình XAI SHAP Waterfall & Top Features
│   │   │       └── ai-advisory/
│   │   │           └── page.tsx             # P04: Khuyến nghị Cố vấn Jev AI & MITRE ATT&CK
│   │   ├── history/
│   │   │   └── page.tsx                     # P05: Nhật ký & Lịch sử phân tích mẫu
│   │   ├── alerts/
│   │   │   ├── page.tsx                     # P06: Trung tâm Quản trị Cảnh báo Đe dọa SOC
│   │   │   └── [id]/
│   │   │       └── page.tsx                 # P07: Quy trình Điều tra & Xử lý Cảnh báo
│   │   ├── system/
│   │   │   └── status/
│   │   │       └── page.tsx                 # P08: Giám sát Authentic Telemetry từ psutil
│   │   ├── evaluation/
│   │   │   └── page.tsx                     # P09: Đánh giá Benchmark Mô hình & Ma trận 2x2
│   │   └── auth/
│   │       └── switch/
│   │           └── page.tsx                 # P10: Chuyển đổi Danh tính Dev (RBAC Switcher)
│   │
│   ├── components/                          # 35 Thành phần giao diện tái sử dụng
│   │   ├── ui/                              # Base UI (Button, Input, Select, Badge, Dialog...)
│   │   ├── metrics/                         # HeroVerdictCard, RadialConfidenceGauge, EvidenceHashBlock
│   │   ├── visualizations/                  # ShapWaterfallChart, ConfusionMatrixHeatmap, TelemetryGauge
│   │   ├── domain/                          # FeatureVectorEditor, SamplePresetLoader, JevAdvisoryContainer
│   │   ├── workflow/                        # AlertStatusStepper, InvestigationNoteEditor, DangerousActionModal
│   │   ├── tables/                          # DataTable, FilterToolbar, PaginationControls
│   │   ├── navigation/                      # SidebarNav, Header, BreadcrumbNav, RoleProfileBadge
│   │   └── feedback/                        # SkeletonCard, InlineFieldError, Toast, BolaErrorView
│   │
│   ├── lib/                                 # Lớp khách API & Tiện ích hệ thống
│   │   ├── api/
│   │   │   ├── client.ts                    # Axios instance, Interceptors & Error Unwrapping
│   │   │   ├── query-keys.ts                # TanStack Query Keys Factory
│   │   │   ├── analysis-service.ts          # API Service cho Analysis Domain
│   │   │   ├── alert-service.ts             # API Service cho Alert Domain
│   │   │   ├── ai-service.ts                # API Service cho Jev AI Domain
│   │   │   ├── system-service.ts            # API Service cho Telemetry & Health
│   │   │   └── evaluation-service.ts        # Static Mock Data Service [STATUS: DESIGN_ONLY / BACKEND_GAP]
│   │   └── utils/
│   │       ├── formatters.ts                # formatBytes, formatUtcDate, formatConfidence
│   │       └── cn.ts                        # clsx + tailwind-merge helper
│   │
│   ├── types/                               # Hợp đồng dữ liệu TypeScript & Zod Schemas
│   │   ├── enums.ts                         # DecisionVerdict, JobStatus, AlertSeverity, AlertStatus, UserRole
│   │   ├── analysis.ts                      # Schemas & Types cho Phân tích PE & Canonical Evidence
│   │   ├── ai.ts                            # Schemas & Types cho Jev AI & MITRE ATT&CK
│   │   ├── alert.ts                         # Schemas & Types cho Cảnh báo SOC
│   │   ├── system.ts                        # Schemas & Types cho Telemetry & Subsystems
│   │   ├── evaluation.ts                    # Schemas & Types cho Benchmark & Confusion Matrix
│   │   └── errors.ts                        # ApiErrorEnvelope & ErrorDetail
│   │
│   ├── hooks/                               # Custom React Hooks
│   │   ├── use-alerts-polling.ts            # Smart Polling hook cho SOC Alerts & System Telemetry
│   │   ├── use-update-alert.ts              # Optimistic Update hook cho cảnh báo SOC
│   │   └── use-auth-session.ts              # Quản lý Bearer Token & Vai trò người dùng
│   │
│   ├── providers/                           # React Context Providers
│   │   ├── query-provider.tsx               # TanStack QueryClientProvider
│   │   └── auth-provider.tsx                # Auth State & RBAC Guard Provider
│   │
│   └── mocks/                               # Mock Service Worker (MSW v2)
│       ├── handlers.ts                      # Bộ xử lý Mock cho các endpoints cốt lõi (MSW v2)
│       ├── server.ts                        # Node.js server cho Vitest
│       └── browser.ts                       # Browser worker cho dev preview
│
├── e2e/                                     # Bộ kiểm thử Playwright End-to-End
│   ├── malware-analysis.spec.ts             # Luồng E2E nộp vector & xem Canonical
│   ├── soc-triage.spec.ts                   # Luồng E2E điều tra & đóng cảnh báo SOC
│   └── security-bola.spec.ts                # Luồng E2E kiểm thử rào chắn BOLA/IDOR
│
├── tailwind.config.js                       # Cấu hình Design Tokens Impeccable
├── tsconfig.json                            # TypeScript Strict Mode Config
└── package.json                             # Dependencies chuẩn hóa
```

---

### 3. TỆP CẤU HÌNH KHỞI ĐỘNG THIẾT YẾU (`package.json`, `tailwind.config.js`)

#### 3.1. `package.json`
```json
{
  "name": "x-sentinel-v3-frontend",
  "version": "3.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint",
    "type-check": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.28.0",
    "axios": "^1.6.8",
    "clsx": "^2.1.0",
    "lucide-react": "^0.359.0",
    "next": "^14.1.4",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "recharts": "^2.12.3",
    "tailwind-merge": "^2.2.2",
    "uuid": "^9.0.1",
    "zod": "^3.22.4"
  },
  "devDependencies": {
    "@axe-core/playwright": "^4.8.5",
    "@playwright/test": "^1.42.1",
    "@testing-library/react": "^14.2.2",
    "@types/node": "^20.11.30",
    "@types/react": "^18.2.69",
    "@types/react-dom": "^18.2.22",
    "@types/uuid": "^9.0.8",
    "autoprefixer": "^10.4.19",
    "msw": "^2.2.8",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.4.3",
    "vitest": "^1.4.0"
  }
}
```

#### 3.2. `tailwind.config.js` (Design Tokens Impeccable)
```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#121418',      // Obsidian Deep (Cấm Pure Black #000000)
          surface: '#181b20',   // Dark Slate
          subtle: '#20252d',    // Muted Slate
        },
        border: {
          subtle: '#29303b',
          prominent: '#3b4554',
        },
        text: {
          primary: '#f1f5f9',   // Slate 100 (Cấm Pure White #ffffff)
          secondary: '#94a3b8', // Slate 400
          muted: '#64748b',     // Slate 500
        },
        accent: {
          brand: '#38bdf8',     // Cyan Electric
        },
        verdict: {
          malicious: '#f43f5e', // Rose Danger
          suspicious: '#f59e0b',// Amber Radiant
          benign: '#10b981',    // Emerald Pure
        },
      },
      borderRadius: {
        // Tuân thủ quy tắc bo góc lồng nhau: R_inner = R_outer - Padding
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
      },
    },
  },
  plugins: [],
};
```

---

### 4. CẨM NANG 5 GIAI ĐOẠN TRIỂN KHAI TỰ HÀNH (AUTONOMOUS EXECUTION GUIDE)

AI Coding Agent hãy thực hiện theo đúng trình tự từng giai đoạn, tự xác minh trước khi chuyển bước:

#### GIAI ĐOẠN 1: HẠ TẦNG & GIAO THỨC (TASKS 01 - 05)
1. Cài đặt các gói phụ thuộc theo `package.json`.
2. Tạo cấu trúc thư mục `src/types/` và dán toàn bộ mã nguồn hợp đồng từ tài liệu `11-DATA-CONTRACTS.md`.
3. Triển khai `src/lib/api/client.ts` từ tài liệu `10-FRONTEND-API-INTEGRATION.md` với đầy đủ interceptors.
4. Cấu hình TanStack Query Provider và trang chuyển token `/auth/switch`.
5. **Xác minh Giai đoạn 1:** Chạy `npm run type-check` đạt 0 lỗi.

#### GIAI ĐOẠN 2: THÀNH PHẦN CƠ SỞ & BẢNG BIỂU (TASKS 06 - 10)
1. Dựng 8 thành phần nguyên tử trong `src/components/ui/` (đảm bảo tỷ lệ đệm nút 2:1 và nhãn Title Case).
2. Dựng Master Layout Shell gồm SidebarNav (260px) và Global Header (64px).
3. Triển khai `SkeletonCard`, `InlineFieldError`, `ToastNotification` và `DataTable` hỗ trợ phân trang.
4. **Xác minh Giai đoạn 2:** Dựng trang mẫu kiểm thử hiển thị đầy đủ các components không có layout shift.

#### GIAI ĐOẠN 3: PHÂN TÍCH PE & CANONICAL EVIDENCE (TASKS 11 - 15)
1. Dựng `FeatureVectorEditor` kiểm tra realtime 2.381 phần tử số thực.
2. Xây dựng trang `/analyze` (P01) với Banner cảnh báo khóa file thô (HTTP 501).
3. Xây dựng `HeroVerdictCard` (Tiêu điểm độc tôn), `RadialConfidenceGauge` và `EvidenceHashBlock`.
4. Hoàn thiện trang `/analysis/{id}` (P02) với kết quả phân tích đồng bộ tức thì và bảng phân rã 5 module M1-M5 (TADR, Tabular STRIP, View Concentration, Cross-View Disagreement, Semantic Plausibility).
5. Hoàn thiện trang `/history` (P05) với bộ lọc đa tiêu chí và xuất báo cáo JSON.
6. **Xác minh Giai đoạn 3:** Chạy kịch bản `E2E-01` nộp vector mẫu và đối soát kết quả Canonical.

#### GIAI ĐOẠN 4: GIẢI TRÌNH XAI, JEV AI & CẢNH BÁO SOC (TASKS 16 - 20)
1. Xây dựng trang `/analysis/{id}/explainability` (P03) với biểu đồ SHAP Waterfall (Top 15 features).
2. Xây dựng trang `/analysis/{id}/ai-advisory` (P04) với khung viền hổ phách, Banner cảnh báo Advisory và bảng ma trận MITRE ATT&CK.
3. Hoàn thiện Trung tâm Cảnh báo `/alerts` (P06) với 4 thẻ KPI và bảng tác chiến SOC.
4. Xây dựng trang `/alerts/{id}` (P07) với `AlertStatusStepper` và `DangerousActionModal` bắt buộc $\ge 20$ ký tự khi đóng cảnh báo.
5. **Xác minh Giai đoạn 4:** Chạy kịch bản `E2E-02` điều tra cảnh báo và đóng báo động giả.

#### GIAI ĐOẠN 5: TELEMETRY, BENCHMARK & BÀN GIAO (TASKS 21 - 25)
1. Xây dựng trang `/system/status` (P08) hiển thị thông số phần cứng thực tế từ `psutil`.
2. Xây dựng trang `/evaluation` (P09) với Ma trận nhầm lẫn 2x2.
3. Bổ sung `BOLAErrorBoundary` bắt chặn lỗi HTTP 403 khi truy cập chéo dữ liệu.
4. Cài đặt MSW v2 và chạy bộ kiểm thử toàn diện Vitest + Playwright.
5. **Xác minh Giai đoạn 5:** Toàn bộ test pass $100\%$, `npm run build` thành công rực rỡ.

---

### 5. BỘ QUY TẮC VÀNG & TIÊU CHUẨN NGHIỆM THU TUYỆT ĐỐI (GOLDEN INVARIANTS)

Trước khi công bố hoàn thành công việc, AI Coding Agent phải tự rà soát danh sách kiểm tra sau:
- [ ] Không có tệp Jinja Template hoặc HTML tĩnh nào được tạo mới trong Backend.
- [ ] Không có đoạn code Python nào trong `backend/` bị chỉnh sửa.
- [ ] Không có màu Pure Black (`#000000`) hay Pure White (`#ffffff`) nào xuất hiện trong CSS/Tailwind.
- [ ] Tỷ lệ đệm của mọi nút bấm tuân thủ $Padding_X = 2 \times Padding_Y$.
- [ ] Mọi quy tắc bo góc lồng nhau tuân thủ $R_{\text{inner}} = R_{\text{outer}} - Padding$.
- [ ] Báo cáo Jev AI luôn có Banner cảnh báo nổi bật màu hổ phách `Advisory Only`.
- [ ] Mọi ô nhập liệu bị lỗi đều có viền đỏ và dòng giải thích inline ngay phía dưới.
- [ ] Không sử dụng Spinner tròn quay ở giữa trang; toàn bộ trạng thái chờ dùng Skeleton Shimmer.
- [ ] Toàn bộ 21 endpoints API được định nghĩa Type-Safe với TypeScript và Zod.
- [ ] Lệnh kiểm thử `npx playwright test` vượt qua $100\%$ các kịch bản.

---

### 6. BẢN ĐỒ ĐIỀU HƯỚNG BỘ TÀI LIỆU KỸ THUẬT (DOCUMENTATION MAP 00 - 15)

Khi cần tra cứu chi tiết kỹ thuật trong quá trình code, hãy mở trực tiếp các tài liệu chuyên đề tương ứng trong thư mục `docs/frontend-handoff/`:

- **00-EXECUTIVE-SUMMARY.md:** Tổng quan điều hành, kết quả kiểm toán 101 tệp Backend và 993 tests.
- **01-SYSTEM-ARCHITECTURE.md:** Kiến trúc 4 tầng, luồng dữ liệu Mermaid, phân hệ đồng bộ/bất đồng bộ.
- **02-FEATURE-INVENTORY.md:** Đặc tả chi tiết A-I của toàn bộ 28 tính năng nghiệp vụ.
- **03-API-CATALOG.md:** Danh mục 21 endpoints, JSON schema request/response và 32 mã lỗi `XS_*`.
- **04-DATABASE-SCHEMA.md:** Lược đồ 13 bảng SQL Server 2022, ràng buộc khóa ngoại và quy tắc hiển thị.
- **05-AUTH-AND-PERMISSIONS.md:** Ma trận phân quyền 4 vai trò, 12 quyền và cơ chế phòng thủ BOLA/IDOR.
- **06-BUSINESS-WORKFLOWS.md:** Sơ đồ tuần tự 8 luồng nghiệp vụ chính và máy trạng thái Job/Alert.
- **07-FRONTEND-PAGE-INVENTORY.md:** Danh mục 10 trang Frontend chính thức và quyền hạn truy cập.
- **08-PAGE-AND-UI-SPECIFICATIONS.md:** Đặc tả chi tiết layout, wireframe ASCII và chuẩn thiết kế Impeccable.
- **09-COMPONENT-INVENTORY.md:** Danh mục 35 components tái sử dụng kèm TypeScript Props Interface.
- **10-FRONTEND-API-INTEGRATION.md:** Thiết kế Axios client, interceptors và caching TanStack Query.
- **11-DATA-CONTRACTS.md:** Hợp đồng dữ liệu đầy đủ 100% bằng TypeScript và Zod schemas.
- **12-FRONTEND-GAP-ANALYSIS.md:** Phân tích 16 khoảng trống kỹ thuật trọng yếu giữa nguyên mẫu cũ và production.
- **13-FRONTEND-IMPLEMENTATION-ROADMAP.md:** Lộ trình 5 giai đoạn và 25 tác vụ kỹ thuật chi tiết.
- **14-FRONTEND-TEST-STRATEGY.md:** Chiến lược kiểm thử 4 tầng, kịch bản Playwright E2E và MSW mocks.
- **15-TRACEABILITY-MATRIX.md:** Ma trận truy vết đa tầng liên kết Feature -> API -> DB -> Page -> Component -> Test.
- **16-FRONTEND-MASTER-BLUEPRINT.md:** (Tài liệu này) Bản thiết kế mẫu toàn năng hướng dẫn AI Agent thực thi.
