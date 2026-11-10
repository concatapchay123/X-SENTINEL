# 11 — HỢP ĐỒNG DỮ LIỆU FRONTEND: TYPESCRIPT & ZOD SCHEMAS (DATA CONTRACTS)
## HỆ THỐNG X-SENTINEL V3 — MALWARE ANALYSIS & THREAT DETECTION PLATFORM

---

### MỤC LỤC
1. [Nguyên Tắc Thiết Kế Hợp Đồng Dữ Liệu Type-Safe](#1-nguyên-tắc-thiết-kế-hợp-đồng-dữ-liệu-type-safe)
2. [Hệ Thống Enum Chuẩn Hóa (Core System Enums)](#2-hệ-thống-enum-chuẩn-hóa-core-system-enums)
3. [Domain 1: Phân Tích Mẫu & Bằng Chứng Canonical (Analysis Contracts)](#3-domain-1-phân-tích-mẫu--bằng-chứng-canonical-analysis-contracts)
4. [Domain 2: Khuyến Nghị Cố Vấn Jev AI & MITRE ATT&CK (Advisory Contracts)](#4-domain-2-khuyến-nghị-cố-vấn-jev-ai--mitre-attck-advisory-contracts)
5. [Domain 3: Quản Lý & Tác Chiến Cảnh Báo SOC (Alert Contracts)](#5-domain-3-quản-lý--tác-chiến-cảnh-báo-soc-alert-contracts)
6. [Domain 4: Authentic Telemetry & Sức Khỏe Hạ Tầng (System Contracts)](#6-domain-4-authentic-telemetry--sức-khỏe-hạ-tầng-system-contracts)
7. [Domain 5: Đánh Giá Hiệu Năng Mô Hình & Benchmark (Evaluation Contracts)](#7-domain-5-đánh-giá-hiệu-năng-mô-hình--benchmark-evaluation-contracts)
8. [Cấu Trúc Phong Bì Lỗi Chuẩn Hóa `XS_*` (Standard Error Envelope)](#8-cấu-trúc-phong-bì-lỗi-chuẩn-hóa-xs_-standard-error-envelope)

---

### 1. NGUYÊN TẮC THIẾT KẾ HỢP ĐỒNG DỮ LIỆU TYPE-SAFE

To toàn bộ các kiểu dữ liệu trong tài liệu này phản ánh chính xác $100\%$ các Pydantic Models của Backend X-SENTINEL V3 tại `backend/src/x_sentinel/api/schemas.py` và `backend/src/x_sentinel/data/schema.py`. Frontend sử dụng đồng thời:
1. **TypeScript Interfaces/Types:** Đảm bảo an toàn kiểu dữ liệu trong thời gian biên dịch (Compile-time Type Safety).
2. **Zod Validation Schemas:** Đảm bảo xác thực dữ liệu đầu vào tại Form và xác thực tính toàn vẹn của phản hồi API trong thời gian chạy (Runtime Boundary Validation).

---

### 2. HỆ THỐNG ENUM CHUẨN HÓA (CORE SYSTEM ENUMS)

Tệp nguồn: `src/types/enums.ts`

```typescript
// Phán quyết xác định tính độc hại của mẫu PE (Canonical Decision Verdict)
export enum DecisionVerdict {
  PASS = 'PASS',
  ALERT = 'ALERT',
  QUARANTINE = 'QUARANTINE',
  DEMO_ONLY = 'DEMO_ONLY',
}

// Trạng thái vòng đời của một tác vụ phân tích (Canonical JobStatus)
export enum JobStatus {
  QUEUED = 'queued',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  QUARANTINED = 'quarantined',
}

// Mức độ nghiêm trọng của cảnh báo đe dọa SOC
export enum AlertSeverity {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
}

// Trạng thái quy trình xử lý cảnh báo SOC (Canonical AlertStatus)
export enum AlertStatus {
  OPEN = 'open',
  ACKNOWLEDGED = 'acknowledged',
  RESOLVED = 'resolved',
  DISMISSED = 'dismissed',
}

// Vai trò người dùng trong hệ thống
export enum UserRole {
  ADMIN = 'admin',
  ANALYST = 'analyst',
  EVALUATOR = 'evaluator',
  OPERATOR = 'operator',
}

// Danh mục 12 quyền hạn cơ bản (Canonical Permissions)
export enum Permission {
  ANALYSIS_SUBMIT = 'analysis:submit',
  ANALYSIS_READ = 'analysis:read',
  ANALYSIS_READ_ALL = 'analysis:read_all',
  EVIDENCE_READ = 'evidence:read',
  ALERTS_READ = 'alerts:read',
  ALERTS_MUTATE = 'alerts:mutate',
  AI_INVOKE = 'ai:invoke',
  AI_READ = 'ai:read',
  AI_FEEDBACK = 'ai:feedback',
  EVALUATION_SCORE = 'evaluation:score',
  CONFIG_WRITE = 'config:write',
  ADMIN_OPS = 'admin:ops',
}
```

---

### 3. DOMAIN 1: PHÂN TÍCH MẪU & BẰNG CHỨNG CANONICAL (ANALYSIS CONTRACTS)

Tệp nguồn: `src/types/analysis.ts`

```typescript
import { z } from 'zod';
import { DecisionVerdict, JobStatus } from './enums';
import { AlertSummarySchema, type AlertSummary } from './alert';

// -------------------------------------------------------------
// 1. Zod Schemas cho Nộp Phân Tích Vector 2.381 Chiều
// -------------------------------------------------------------
export const AnalyzeSubmitRequestSchema = z.object({
  features: z
    .array(z.number().refine(Number.isFinite, { message: 'Must be finite float' }))
    .length(2381, { message: 'Vector đặc trưng bắt buộc phải có chính xác 2.381 phần tử số thực hữu hạn (finite float)' }),
  source_name: z.string().max(255).optional(),
  request_id: z.string().max(128).optional(),
});

export type AnalyzeSubmitRequest = z.infer<typeof AnalyzeSubmitRequestSchema>;
export const VectorAnalysisRequestSchema = AnalyzeSubmitRequestSchema;
export type VectorAnalysisRequest = AnalyzeSubmitRequest;

// Phản hồi đồng bộ ngay lập tức từ POST /v1/analyze/vector
export const AnalysisResponseSchema = z.object({
  request_id: z.string(),
  status: z.string(), // 'completed', 'DEMO_ONLY', 'quarantined'
  demo_mode: z.boolean(),
  malware_score: z.number().min(0.0).max(1.0),
  signals: z.record(z.number()), // m1 through m5
  suspicion_score: z.number().min(0.0).max(1.0),
  threshold: z.number().nullable().optional(),
  decision: z.nativeEnum(DecisionVerdict).nullable().optional(),
  view_contributions: z.record(z.number()).default({}), // structural, behavioral, metadata
  warnings: z.array(z.string()).default([]),
  evidence_ref: z.string().nullable().optional(),
  job_id: z.string().uuid().nullable().optional(),
});

export type AnalysisResponse = z.infer<typeof AnalysisResponseSchema>;
export type AnalyzeSubmitResponse = AnalysisResponse;

// -------------------------------------------------------------
// 2. Chi Tiết Kết Quả & Canonical Evidence
// -------------------------------------------------------------
export const DetectorScoreItemSchema = z.object({
  detector_code: z.enum(['M1', 'M2', 'M3', 'M4', 'M5']),
  score: z.number().min(0.0).max(1.0),
  diagnostics: z.record(z.any()).default({}),
});

export type DetectorScoreItem = z.infer<typeof DetectorScoreItemSchema>;

export const AnalysisResultDetailSchema = z.object({
  malware_score: z.number().nullable().optional(),
  suspicion_score: z.number().nullable().optional(),
  threshold: z.number().nullable().optional(),
  decision: z.string(), // pass, alert, quarantine, unknown
  latency_ms: z.number().nullable().optional(),
  view_contributions: z.record(z.number()).default({}),
  evidence_uri: z.string().nullable().optional(),
  result_json: z.record(z.any()).default({}),
});

export type AnalysisResultDetail = z.infer<typeof AnalysisResultDetailSchema>;

export const AnalysisDetailResponseSchema = z.object({
  id: z.string().uuid(),
  request_id: z.string(),
  status: z.nativeEnum(JobStatus),
  input_mode: z.enum(['vector', 'raw_pe']),
  input_sha256: z.string().nullable().optional(),
  demo_mode: z.boolean(),
  created_at: z.string().datetime({ offset: true }),
  completed_at: z.string().datetime({ offset: true }).nullable().optional(),
  error_code: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  result: AnalysisResultDetailSchema.nullable().optional(),
  scores: z.array(DetectorScoreItemSchema).default([]),
  alerts: z.array(AlertSummarySchema).default([]), // Liên kết danh sách AlertSummary chuẩn từ ./alert
  evidence_ref: z.string().nullable().optional(),
});

export type AnalysisDetailResponse = z.infer<typeof AnalysisDetailResponseSchema>;

// Canonical Evidence Response từ GET /v1/analysis/{id}/evidence (RFC 8785 / JCS)
export const CanonicalEvidenceResponseSchema = z.object({
  request_id: z.string(),
  run_id: z.string(),
  timestamp: z.string().datetime({ offset: true }),
  code_commit: z.string(),
  build_digest: z.string(),
  input_id: z.string(),
  input_mode: z.enum(['vector', 'raw_pe']),
  view_map_hash: z.string().length(64),
  model_hash: z.string().length(64),
  model_config_hash: z.string().length(64),
  detector_config_hash: z.string().length(64),
  seed: z.number().int(),
  malware_score: z.number().min(0.0).max(1.0),
  signals: z.record(z.number()),
  fusion_score: z.number().min(0.0).max(1.0),
  threshold_id: z.string(),
  decision: z.string(),
  latency_ms: z.record(z.number()),
  demo_mode: z.boolean(),
  evidence_hash: z.string().length(64),
  verified: z.boolean().default(true),
});

export type CanonicalEvidenceResponse = z.infer<typeof CanonicalEvidenceResponseSchema>;

// LƯU Ý BẢO TOÀN DỮ LIỆU XAI / SHAP (DATA AVAILABILITY INVARIANT - GAP-14):
// - `view_contributions` (Structural, Behavioral, Metadata) và điểm `scores` M1-M5:
//   Có sẵn từ endpoint `GET /v1/analysis/{id}`.
// - Chi tiết 15 đặc trưng SHAP Waterfall và giá trị đặc trưng thô (Raw Feature Values):
//   HIỆN CHƯA CÓ TRONG REST API (Backend Gap). Backend chỉ bóc tách SHAP nội bộ để tính M1/M3,
//   chưa lưu trữ hay trả về mảng 2.381 giá trị SHAP qua HTTP.
// - Frontend P03 hiển thị biểu đồ 3-View thực tế và gắn nhãn [DESIGN_ONLY / MOCK] cho Waterfall.

// -------------------------------------------------------------
// 3. Trạng Thái & Lịch Sử Danh Sách (History Contracts)
// -------------------------------------------------------------

// Tham số truy vấn máy chủ (Server Query Params cho GET /v1/analysis)
// BẤT BIẾN BACKEND: Máy chủ chỉ chấp nhận limit, offset, status, decision, input_mode, demo_mode.
// Không có các tham số search, page, date_from, date_to trên server.
export const AnalysisServerQueryParamsSchema = z.object({
  limit: z.number().int().min(1).max(1000).default(50),
  offset: z.number().int().min(0).default(0),
  status: z.enum(['completed', 'failed', 'quarantined', 'running', 'queued']).optional(),
  decision: z.enum(['pass', 'alert', 'quarantine']).optional(),
  input_mode: z.enum(['vector', 'raw_pe']).optional(),
  demo_mode: z.boolean().optional(),
});

export type AnalysisServerQueryParams = z.infer<typeof AnalysisServerQueryParamsSchema>;

// Trạng thái bộ lọc và phân trang phía Client (UI Filter State)
export interface AnalysisClientFilterState {
  page: number; // 1-indexed, ánh xạ sang offset = (page - 1) * limit khi gửi lên máy chủ
  limit: number;
  status?: string;
  decision?: string;
  input_mode?: string;
  demo_mode?: boolean;
  search?: string;     // [Client-side Filter: Lọc cục bộ trên mảng items đã tải]
  date_from?: string;  // [Client-side Filter: Lọc cục bộ theo created_at]
  date_to?: string;    // [Client-side Filter: Lọc cục bộ theo created_at]
}

// Hàm chuyển đổi an toàn từ Client Filter State sang Server Query Params
export function toAnalysisQueryParams(clientState: AnalysisClientFilterState): AnalysisServerQueryParams {
  return {
    limit: clientState.limit,
    offset: Math.max(0, (clientState.page - 1) * clientState.limit),
    status: clientState.status as any,
    decision: clientState.decision as any,
    input_mode: clientState.input_mode as any,
    demo_mode: clientState.demo_mode,
  };
}

export const AnalysisFilterParamsSchema = AnalysisServerQueryParamsSchema;
export type AnalysisFilterParams = AnalysisServerQueryParams;

export const AnalysisJobSummarySchema = z.object({
  id: z.string().uuid(),
  request_id: z.string(),
  status: z.nativeEnum(JobStatus),
  input_mode: z.string(),
  demo_mode: z.boolean(),
  decision: z.string().nullable().optional(),
  malware_score: z.number().nullable().optional(),
  suspicion_score: z.number().nullable().optional(),
  created_at: z.string().datetime({ offset: true }),
  completed_at: z.string().datetime({ offset: true }).nullable().optional(),
});

export type AnalysisJobSummary = z.infer<typeof AnalysisJobSummarySchema>;

export const AnalysisListResponseSchema = z.object({
  items: z.array(AnalysisJobSummarySchema),
  total: z.number().int().min(0),
  limit: z.number().int().min(1),
  offset: z.number().int().min(0),
});

export type AnalysisListResponse = z.infer<typeof AnalysisListResponseSchema>;
```

---

### 4. DOMAIN 2: KHUYẾN NGHỊ CỐ VẤN JEV AI & ĐIỀU PHỐI ADVISORY (ADVISORY CONTRACTS)

Tệp nguồn: `src/types/ai.ts`

```typescript
import { z } from 'zod';

// Chế độ suy luận cố vấn của Jev AI
export enum JevAIMode {
  EXPLAIN = 'explain',
  TRIAGE = 'triage',
  COMPARE = 'compare',
  REPORT = 'report',
  DOCS = 'docs',
}

// Trạng thái vòng đời của một lượt chạy Jev AI
export enum JevAIRunStatus {
  QUEUED = 'queued',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  BLOCKED = 'blocked',
}

// Payload yêu cầu thực thi suy luận Jev AI (POST /v1/ai/explain)
export const JevExplainRequestSchema = z.object({
  analysis_id: z.string().min(1).max(128),
  mode: z.enum(['explain', 'triage', 'compare', 'report', 'docs']).default('explain'),
  compare_with_analysis_id: z.string().nullable().optional(),
  focus_signals: z.array(z.enum(['m1', 'm2', 'm3', 'm4', 'm5'])).nullable().optional(),
  question: z.string().max(500).nullable().optional(),
});

export type JevExplainRequest = z.infer<typeof JevExplainRequestSchema>;

// Phản hồi chi tiết lượt chạy Jev AI (POST /v1/ai/explain, GET /v1/ai/runs/{run_id})
export const JevAIRunResponseSchema = z.object({
  id: z.string().uuid(), // BẤT BIẾN BACKEND: Khóa chính UUID của lượt chạy AI (định danh là `id`)
  analysis_job_id: z.string().uuid().nullable().optional(),
  requested_by_user_id: z.string().uuid().nullable().optional(),
  mode: z.enum(['explain', 'triage', 'compare', 'report', 'docs']),
  status: z.enum(['queued', 'running', 'completed', 'failed', 'blocked']),
  advisory_only: z.literal(true), // BẤT BIẾN: Luôn là true, không bao giờ thay thế Canonical Evidence
  authoritative_decision_unchanged: z.literal(true),
  model_id: z.string(), // Cấu hình động từ backend (mặc định 'jev-local-TBD')
  endpoint_label: z.string().default('lm_studio_local'),
  prompt_version: z.string(),
  input_digest_sha256: z.string().length(64),
  output_digest_sha256: z.string().length(64).nullable().optional(),
  context_summary: z.record(z.any()).default({}),
  response_text: z.string().nullable().optional(), // Văn bản nhận định Markdown tự do
  decision_result: z.record(z.any()).nullable().optional(),
  latency_ms: z.number().nullable().optional(),
  error_code: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  created_at: z.string().datetime({ offset: true }),
  completed_at: z.string().datetime({ offset: true }).nullable().optional(),
});

export type JevAIRunResponse = z.infer<typeof JevAIRunResponseSchema>;

// Danh sách các lượt chạy Jev AI (GET /v1/ai/runs)
export const JevAIRunListResponseSchema = z.object({
  items: z.array(JevAIRunResponseSchema),
  total: z.number().int().min(0),
  limit: z.number().int().min(1),
  offset: z.number().int().min(0),
});

export type JevAIRunListResponse = z.infer<typeof JevAIRunListResponseSchema>;

// Payload gửi phản hồi đánh giá chất lượng nhận định AI (POST /v1/ai/runs/{run_id}/feedback)
export const JevFeedbackRequestSchema = z.object({
  rating: z.number().int().min(1).max(5).nullable().optional(),
  label: z.enum(['helpful', 'not_helpful', 'incorrect', 'unsafe', 'unclear']).nullable().optional(),
  comment: z.string().max(2000).nullable().optional(),
});

export type JevFeedbackRequest = z.infer<typeof JevFeedbackRequestSchema>;

// Phản hồi sau khi lưu đánh giá (POST / GET /v1/ai/runs/{run_id}/feedback)
export const JevFeedbackResponseSchema = z.object({
  id: z.string().uuid(),
  jev_ai_run_id: z.string().uuid(),
  user_id: z.string().uuid().nullable().optional(),
  rating: z.number().int().nullable().optional(),
  label: z.string().nullable().optional(),
  comment: z.string().nullable().optional(),
  advisory_only: z.literal(true).default(true),
  created_at: z.string().datetime({ offset: true }),
});

export type JevFeedbackResponse = z.infer<typeof JevFeedbackResponseSchema>;

export const JevFeedbackListResponseSchema = z.object({
  jev_ai_run_id: z.string().uuid(),
  total: z.number().int().min(0),
  items: z.array(JevFeedbackResponseSchema),
});

export type JevFeedbackListResponse = z.infer<typeof JevFeedbackListResponseSchema>;
```

---

### 5. DOMAIN 3: QUẢN LÝ & TÁC CHIẾN CẢNH BÁO SOC (ALERT CONTRACTS)

Tệp nguồn: `src/types/alert.ts`

```typescript
import { z } from 'zod';
import { AlertSeverity, AlertStatus } from './enums';

export const AlertSummarySchema = z.object({
  id: z.string().uuid(),
  analysis_job_id: z.string().uuid(), // BẤT BIẾN: Định danh liên kết Analysis Job (không dùng analysis_id)
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  status: z.enum(['open', 'acknowledged', 'resolved', 'dismissed']),
  reason: z.string(), // Nguyên nhân kích hoạt cảnh báo từ bộ phát hiện M1-M5
  created_at: z.string().datetime({ offset: true }),
  resolved_at: z.string().datetime({ offset: true }).nullable(),
});

export type AlertSummary = z.infer<typeof AlertSummarySchema>;
// Alias tương thích giao diện
export const AlertItemSchema = AlertSummarySchema;
export type AlertItem = AlertSummary;

// Tham số truy vấn máy chủ (Server Query Params cho GET /v1/alerts)
export const AlertQueryParamsSchema = z.object({
  limit: z.number().int().min(1).max(1000).default(50),
  offset: z.number().int().min(0).default(0),
  severity: z.enum(['low', 'medium', 'high', 'critical']).optional(),
  status: z.enum(['open', 'acknowledged', 'resolved', 'dismissed']).optional(),
  analysis_job_id: z.string().uuid().optional(),
});

export type AlertQueryParams = z.infer<typeof AlertQueryParamsSchema>;

// Trạng thái bộ lọc và phân trang phía Client (UI Filter State)
export interface AlertClientFilterState {
  page: number; // 1-indexed, ánh xạ sang offset = (page - 1) * limit
  limit: number;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  status?: 'open' | 'acknowledged' | 'resolved' | 'dismissed';
  analysis_job_id?: string;
}

// Phản hồi danh sách cảnh báo từ máy chủ (GET /v1/alerts)
export const AlertListResponseSchema = z.object({
  items: z.array(AlertSummarySchema),
  total: z.number().int().min(0),
  limit: z.number().int().min(1),
  offset: z.number().int().min(0), // BẤT BIẾN: Máy chủ dùng offset, không trả page hay counters
});

export type AlertListResponse = z.infer<typeof AlertListResponseSchema>;

// Client View Model cho bảng cảnh báo (tính toán các chỉ số thống kê cục bộ theo trang hiện tại)
// BẤT BIẾN DỮ LIỆU: current_page_critical_count và current_page_active_count phản ánh phạm vi
// các bản ghi đã tải trong trang hiện tại (Current Page Scope), KHÔNG phải tổng số toàn hệ thống.
// Tổng số bản ghi khớp bộ lọc trên toàn hệ thống được phản ánh qua trường `total` từ máy chủ.
export interface AlertListClientViewModel {
  items: AlertSummary[];
  total: number;
  page: number;
  limit: number;
  current_page_critical_count: number; // Tính toán tại Client trên trang hiện tại: items.filter(a => a.severity === 'critical').length
  current_page_active_count: number;   // Tính toán tại Client trên trang hiện tại: items.filter(a => a.status === 'open').length
  /** @deprecated Sử dụng current_page_critical_count để tránh nhầm lẫn với tổng số toàn hệ thống */
  critical_count?: number;
  /** @deprecated Sử dụng current_page_active_count để tránh nhầm lẫn với tổng số toàn hệ thống */
  active_count?: number;
}

// Payload cập nhật trạng thái cảnh báo gửi lên máy chủ (PATCH /v1/alerts/{alert_id})
// BẤT BIẾN HỢP ĐỒNG BACKEND: Máy chủ chỉ chấp nhận { status: string }.
// Không có các trường assignee_id hoặc investigation_notes trong CSDL hay API body.
export const AlertStatusUpdateRequestSchema = z.object({
  status: z.enum(['acknowledged', 'resolved', 'dismissed']),
});

export type AlertStatusUpdateRequest = z.infer<typeof AlertStatusUpdateRequestSchema>;

// Schema mở rộng tại tầng Client State phục vụ giao diện điều tra viên SOC
// LƯU Ý BẢO MẬT & KIẾN TRÚC:
// - Backend KHÔNG lưu trữ ghi chú điều tra hay người xử lý (đây là UI Gap / GAP-15).
// - Frontend TUYỆT ĐỐI KHÔNG được lưu trữ các ghi chú điều tra nhạy cảm vào localStorage không mã hóa.
//   Mọi ghi chú nháp trong phiên được lưu trong bộ nhớ tạm (In-Memory State) và sẽ biến mất khi rời phiên làm việc.
// - Quy tắc bắt buộc 20 ký tự khi DISMISSED là quy tắc kiểm tra giao diện (Client-side validation)
//   trước khi gửi lệnh cập nhật status: "dismissed" lên server.
export const AlertClientUpdatePayloadSchema = z
  .object({
    status: z.enum(['acknowledged', 'resolved', 'dismissed']),
    investigation_notes: z.string().optional(), // [UI Gap GAP-15: Chỉ xử lý cục bộ trên giao diện in-memory]
  })
  .refine(
    (data) => {
      if (data.status === 'dismissed') {
        return !!data.investigation_notes && data.investigation_notes.trim().length >= 20;
      }
      return true;
    },
    {
      message: 'Khi đánh dấu đóng hoặc bỏ qua cảnh báo (DISMISSED), bắt buộc phải nhập ghi chú điều tra tối thiểu 20 ký tự trên giao diện.',
      path: ['investigation_notes'],
    }
  );

export type AlertClientUpdatePayload = z.infer<typeof AlertClientUpdatePayloadSchema>;
export type AlertUpdatePayload = AlertStatusUpdateRequest;
```

---

### 6. DOMAIN 4: AUTHENTIC TELEMETRY & SỨC KHỎE HẠ TẦNG (SYSTEM CONTRACTS)

Tệp nguồn: `src/types/system.ts`

```typescript
import { z } from 'zod';

export const HealthCheckResponseSchema = z.object({
  status: z.string(),
  service: z.string().optional(),
  version: z.string().optional(),
  environment: z.string().optional(),
  demo_mode: z.boolean().optional(),
  input_mode: z.string().optional(),
  jev_ai_enabled: z.boolean().optional(),
});

export type HealthCheckResponse = z.infer<typeof HealthCheckResponseSchema>;

export const ReadinessCheckResponseSchema = z.object({
  status: z.enum(['ready', 'not_ready']),
  service: z.string().optional(),
  version: z.string().optional(),
  environment: z.string().optional(),
  demo_mode: z.boolean().optional(),
  input_mode: z.string().optional(),
  database: z.union([z.string(), z.record(z.any())]).nullable().optional(),
  database_revision: z.string().nullable().optional(),
  database_revision_status: z.string().nullable().optional(),
  readiness_blocking: z.boolean().optional(),
  blockers: z.array(z.string()).default([]),
  jev_ai: z.object({
    enabled: z.boolean(),
    status: z.string(),
    model_id: z.string().nullable().optional(),
    prompt_version: z.string().optional(),
    endpoint_label: z.string().optional(),
    advisory_only: z.boolean().optional(),
    local_only: z.boolean().optional(),
  }).optional(),
});

export type ReadinessCheckResponse = z.infer<typeof ReadinessCheckResponseSchema>;

export const SystemConfigStatusResponseSchema = z.object({
  environment: z.string(),
  demo_mode: z.boolean(),
  input_mode: z.string(),
  database_required: z.boolean(),
  database_status: z.string().nullable().optional(),
  database_revision: z.string().nullable().optional(),
  database_revision_status: z.string().nullable().optional(),
  expected_database_revision: z.string().nullable().optional(),
  scientific_config_status: z.string(),
  jev_ai: z.object({
    enabled: z.boolean(),
    status: z.string(),
    model_id: z.string().nullable().optional(),
    prompt_version: z.string(),
    endpoint_label: z.string(),
    advisory_only: z.boolean(),
    local_only: z.boolean(),
  }),
});

export type SystemConfigStatusResponse = z.infer<typeof SystemConfigStatusResponseSchema>;

export const SubsystemHealthSchema = z.object({
  name: z.string(),
  status: z.enum(['HEALTHY', 'DEGRADED', 'UNHEALTHY']),
  message: z.string().optional(),
  metrics: z.record(z.any()).optional(),
});

export type SubsystemHealth = z.infer<typeof SubsystemHealthSchema>;

export const CpuTelemetrySchema = z.object({
  utilization_percent: z.number().min(0.0).max(100.0),
  logical_cores: z.number().int().min(1).nullable(),
  physical_cores: z.number().int().min(1).nullable(),
});

export type CpuTelemetry = z.infer<typeof CpuTelemetrySchema>;

export const MemoryTelemetrySchema = z.object({
  total_bytes: z.number().int().min(0),
  available_bytes: z.number().int().min(0),
  used_bytes: z.number().int().min(0),
  used_percent: z.number().min(0.0).max(100.0),
});

export type MemoryTelemetry = z.infer<typeof MemoryTelemetrySchema>;

export const ProcessTelemetrySchema = z.object({
  pid: z.number().int(),
  rss_bytes: z.number().int().min(0),
  vms_bytes: z.number().int().min(0),
  thread_count: z.number().int().min(1),
});

export type ProcessTelemetry = z.infer<typeof ProcessTelemetrySchema>;

// BẤT BIẾN: Dữ liệu phần cứng chân thực trích xuất từ thư viện psutil (nested DTO)
// Trả về từ endpoint GET /v1/system/telemetry (không chứa chỉ số disk giả lập)
export const AuthenticTelemetryResponseSchema = z.object({
  status: z.enum(['ok', 'degraded']),
  cpu: CpuTelemetrySchema.optional(),
  memory: MemoryTelemetrySchema.optional(),
  process: ProcessTelemetrySchema.optional(),
  error: z.string().optional(),
});

export type AuthenticTelemetryResponse = z.infer<typeof AuthenticTelemetryResponseSchema>;

// LƯU Ý DỮ LIỆU GIÁM SÁT P08 (P08 TELEMETRY DATA AVAILABILITY - GAP-16):
// 1. Dữ liệu CÓ TRONG HỢP ĐỒNG BACKEND:
//    - CPU, RAM, Process: Từ GET /v1/system/telemetry
//    - Liveness, Service Version, Demo Mode: Từ GET /health
//    - Database OK/Status/Latency, Jev AI Status, Blockers: Từ GET /ready
//    - Environment, Revision, Config: Từ GET /v1/config/status
// 2. Dữ liệu KHÔNG ĐƯỢC BACKEND CUNG CẤP (BACKEND_GAP / UNSUPPORTED):
//    - Hostname máy chủ, Tên chi tiết Hệ điều hành, Python Runtime Version
//    - Uptime máy chủ (Days, Hours, Minutes)
//    - Database Connection Pool size (18/50 Active)
//    - ML Concurrency Slots (50 Free)
//    - Jev AI Queue Depth (4/16 Active)
// 3. Quy chuẩn Frontend P08: Chỉ kết xuất các widget có dữ liệu thực tế từ API.
//    Các widget thiếu nguồn dữ liệu phải để N/A hoặc ẩn, tuyệt đối không bịa số liệu.
```

---

### 7. DOMAIN 5: ĐÁNH GIÁ HIỆU NĂNG MÔ HÌNH & BENCHMARK (EVALUATION CONTRACTS) [STATUS: BACKEND_GAP / DESIGN_ONLY]

> [!NOTE]
> Backend hiện tại chưa có HTTP endpoint `/v1/evaluate`. Các schema dưới đây dùng cho Mock Service hoặc tích hợp khi Backend mở rộng endpoint.

Tệp nguồn: `src/types/evaluation.ts`

```typescript
import { z } from 'zod';

export const ConfusionMatrixSchema = z.object({
  true_benign: z.number().int().min(0),
  false_malicious: z.number().int().min(0), // False Positive
  false_benign: z.number().int().min(0),    // False Negative
  true_malicious: z.number().int().min(0),  // True Positive
});

export type ConfusionMatrix = z.infer<typeof ConfusionMatrixSchema>;

export const BenchmarkReportSchema = z.object({
  benchmark_id: z.string().uuid(),
  dataset_name: z.string(),
  sample_count: z.number().int().min(1),
  threshold: z.number().min(0.0).max(1.0),
  accuracy: z.number().min(0.0).max(1.0),
  f1_score: z.number().min(0.0).max(1.0),
  false_positive_rate: z.number().min(0.0).max(1.0),
  auc_roc: z.number().min(0.0).max(1.0),
  confusion_matrix: ConfusionMatrixSchema,
  evaluated_at: z.string().datetime({ offset: true }),
});

export type BenchmarkReport = z.infer<typeof BenchmarkReportSchema>;

export const RunBenchmarkPayloadSchema = z.object({
  dataset_name: z.string(),
  threshold: z.number().min(0.01).max(0.99).default(0.50),
});

export type RunBenchmarkPayload = z.infer<typeof RunBenchmarkPayloadSchema>;
```

---

### 8. CẤU TRÚC PHONG BÌ LỖI CHUẨN HÓA `XS_*` (STANDARD ERROR ENVELOPE)

Tệp nguồn: `src/types/errors.ts`

```typescript
import { z } from 'zod';

export const ErrorDetailSchema = z.object({
  code: z.string().regex(/^XS_[A-Z0-9_]+$/, { message: 'Mã lỗi phải có tiền tố XS_' }),
  message: z.string(),
  details: z.record(z.any()).optional(),
});

export type ErrorDetail = z.infer<typeof ErrorDetailSchema>;

export const ApiErrorEnvelopeSchema = z.object({
  detail: ErrorDetailSchema,
});

export type ApiErrorEnvelope = z.infer<typeof ApiErrorEnvelopeSchema>;
```
