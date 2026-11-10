# 10 — HƯỚNG DẪN TÍCH HỢP API & QUẢN LÝ DỮ LIỆU FRONTEND (API INTEGRATION GUIDE)
## HỆ THỐNG X-SENTINEL V3 — MALWARE ANALYSIS & THREAT DETECTION PLATFORM

---

### MỤC LỤC
1. [Thiết Kế Lớp Khách HTTP Chuẩn Hóa (Standardized HTTP Client Architecture)](#1-thiết-kế-lớp-khách-http-chuẩn-hóa-standardized-http-client-architecture)
2. [Cơ Chế Đánh Chặn Yêu Cầu & Phản Hồi (Interceptors Pipeline)](#2-cơ-chế-đánh-chặn-yêu-cầu--phản-hồi-interceptors-pipeline)
   - [2.1. Request Interceptor: Nạp Bearer Token & Mã Vết `X-Request-ID`](#21-request-interceptor-nạp-bearer-token--mã-vết-x-request-id)
   - [2.2. Response Interceptor: Chuẩn Hóa Lỗi & Xử Lý Mã Lỗi `XS_*`](#22-response-interceptor-chuẩn-hóa-lỗi--xử-lý-mã-lỗi-xs_)
3. [Bộ API Service Modules Đầy Đủ (Complete API Services)](#3-bộ-api-service-modules-đầy-đủ-complete-api-services)
   - [3.1. `analysisService` (Phân Tích Mẫu & Lịch Sử)](#31-analysisservice-phân-tích-mẫu--lịch-sử)
   - [3.2. `alertService` (Quản Lý & Tác Chiến Cảnh Báo SOC)](#32-alertservice-quản-lý--tác-chiến-cảnh-báo-soc)
   - [3.3. `aiService` (Khuyến Nghị Cố Vấn Jev AI)](#33-aiservice-khuyến-nghị-cố-vấn-jev-ai)
   - [3.4. `systemService` (Authentic Telemetry & Sức Khỏe Node)](#34-systemservice-authentic-telemetry--sức-khỏe-node)
   - [3.5. `evaluationService` (Benchmark & Đánh Giá AI)](#35-evaluationservice-benchmark--đánh-giá-ai)
4. [Tích Hợp TanStack Query (React Query v5) & Cơ Chế Bộ Nhớ Đệm (Caching Strategy)](#4-tích-hợp-tanstack-query-react-query-v5--cơ-chế-bộ-nhớ-đệm-caching-strategy)
   - [4.1. Factory Khóa Truy Vấn Toàn Cục (`queryKeys`)](#41-factory-khóa-truy-vấn-toàn-cục-querykeys)
   - [4.2. Thời Gian Hiệu Lực Dữ Liệu (Stale Times & Cache Times)](#42-thời-gian-hiệu-lực-dữ-liệu-stale-times--cache-times)
   - [4.3. Quản Lý Trạng Thái Chi Tiết Phân Tích (Analysis Detail State Management)](#43-quản-lý-trạng-thái-chi-tiết-phân-tích-analysis-detail-state-management)
   - [4.4. Cập Nhật Lạc Quan (Optimistic Updates) Cho Trạng Thái Cảnh Báo](#44-cập-nhật-lạc-quan-optimistic-updates-cho-trạng-thái-cảnh-báo)

---

### 1. THIẾT KẾ LỚP KHÁCH HTTP CHUẨN HÓA (STANDARDIZED HTTP CLIENT ARCHITECTURE)

Toàn bộ các yêu cầu HTTP từ Frontend tới Backend X-SENTINEL V3 đều được tập trung hóa qua phiên bản Axios singleton cấu hình chặt chẽ tại `src/lib/api/client.ts`:

```typescript
// src/lib/api/client.ts
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { v4 as uuidv4 } from 'uuid';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // Giới hạn chờ 30 giây
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});
```

---

### 2. CƠ CHẾ ĐÁNH CHẶN YÊU CẦU & PHẢN HỒI (INTERCEPTORS PIPELINE)

#### 2.1. Request Interceptor: Nạp Bearer Token & Mã Vết `X-Request-ID`
Trước khi mỗi request rời trình duyệt, interceptor tự động:
1. Đính kèm mã định danh vết `X-Request-ID` (UUIDv4) để phục vụ tương quan log phía Backend.
2. Đọc token xác thực từ `localStorage` (hoặc Auth State) và chèn vào Header `Authorization: Bearer <token>`.

```typescript
// src/lib/api/client.ts (tiếp tục)
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 1. Chèn X-Request-ID phục vụ phân tích log
    config.headers['X-Request-ID'] = uuidv4();

    // 2. Chèn Bearer Token nếu có trong phiên (BẤT BIẾN AN NINH: Không fallback token mặc định)
    if (typeof window !== 'undefined') {
      const activeToken = localStorage.getItem('x_sentinel_token');
      if (activeToken && activeToken.trim()) {
        config.headers['Authorization'] = `Bearer ${activeToken.trim()}`;
      }
      // Khi không có token: Không tự động gắn header Authorization,
      // request sẽ gửi đi dưới dạng anonymous và backend sẽ trả về 401 XS_UNAUTHENTICATED đối với các route bảo vệ.
    }

    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);
```

#### 2.2. Response Interceptor: Chuẩn Hóa Lỗi & Xử Lý Mã Lỗi `XS_*`
Backend X-SENTINEL V3 trả về cấu trúc lỗi chuẩn hóa dạng:
`{ "detail": { "code": "XS_...", "message": "..." } }`

Response Interceptor có nhiệm vụ bóc tách cấu trúc này và kích hoạt các phản ứng hệ thống phù hợp:

```typescript
// src/lib/api/client.ts (tiếp tục)
import { toast } from '@/components/feedback/toast';

export interface AppApiError {
  status: number;
  code: string;
  message: string;
  requestId?: string;
}

apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError<{ detail?: { code?: string; message?: string } | string }>) => {
    const status = error.response?.status || 500;
    const detail = error.response?.data?.detail;
    
    let errorCode = 'XS_UNKNOWN_ERROR';
    let errorMessage = 'Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau.';

    if (typeof detail === 'object' && detail !== null) {
      errorCode = detail.code || errorCode;
      errorMessage = detail.message || errorMessage;
    } else if (typeof detail === 'string') {
      errorMessage = detail;
    }

    const appError: AppApiError = {
      status,
      code: errorCode,
      message: errorMessage,
      requestId: error.config?.headers?.['X-Request-ID'] as string,
    };

    // Xử lý các mã lỗi đặc thù của hệ thống X-SENTINEL
    switch (status) {
      case 401:
        // Hết hạn hoặc sai token -> chuyển hướng sang màn hình switch role
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/auth/switch')) {
          toast.error('Phiên làm việc hết hạn hoặc không hợp lệ. Vui lòng cấp lại token.');
          window.location.href = '/auth/switch';
        }
        break;

      case 403:
        // Vi phạm bảo vệ BOLA/IDOR hoặc thiếu quyền RBAC
        toast.error(`Từ chối truy cập (403): ${errorMessage}`);
        break;

      case 429:
        // Vượt ngưỡng tải song song (50 Detector hoặc 4 AI Engine)
        if (errorCode === 'XS_DETECTOR_OVERLOADED') {
          toast.warning('Bộ suy luận Detector đang quá tải (>50 tác vụ). Đang tự động xếp hàng đợi...');
        } else if (errorCode === 'XS_AI_OVERLOADED') {
          toast.warning('Hàng đợi Jev AI đã đầy (>16 tác vụ). Vui lòng thử lại sau giây lát.');
        }
        break;

      case 501:
        // Tính năng bị khóa an toàn (Raw PE upload hoặc AI Ask)
        toast.info(`Tính năng tạm thời vô hiệu hóa: ${errorMessage}`);
        break;

      case 503:
        // Phân hệ AI LM Studio hoặc Database ngoại tuyến
        toast.error(`Dịch vụ tạm thời không khả dụng (503): ${errorMessage}`);
        break;
    }

    return Promise.reject(appError);
  }
);
```

---

### 3. BỘ API SERVICE MODULES ĐẦY ĐỦ (COMPLETE API SERVICES)

#### 3.1. `analysisService` (Phân Tích Mẫu & Lịch Sử)
Tệp nguồn: `src/lib/api/analysis-service.ts`

```typescript
import { apiClient } from './client';
import { 
  VectorAnalysisRequestSchema,
  AnalysisResponseSchema,
  AnalyzeSubmitRequest, 
  AnalyzeSubmitResponse, 
  AnalysisDetailResponse, 
  AnalysisDetailResponseSchema,
  CanonicalEvidenceResponse,
  CanonicalEvidenceResponseSchema,
  AnalysisListResponse,
  AnalysisListResponseSchema,
  AnalysisServerQueryParams,
  AnalysisClientFilterState,
  toAnalysisQueryParams
} from '@/types/analysis';

export class SchemaValidationError extends Error {
  constructor(message: string, public readonly originalError: unknown) {
    super(message);
    this.name = 'SchemaValidationError';
  }
}

export const analysisService = {
  // Nộp phân tích vector 2.381 chiều (Xử lý đồng bộ, runtime validation)
  submitAnalysis: async (payload: AnalyzeSubmitRequest): Promise<AnalyzeSubmitResponse> => {
    const validPayload = VectorAnalysisRequestSchema.parse(payload);
    const res = await apiClient.post<unknown>('/v1/analyze/vector', validPayload);
    const parseResult = AnalysisResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new SchemaValidationError(
        `AnalysisResponse validation failed: ${parseResult.error.message}`,
        parseResult.error
      );
    }
    return parseResult.data;
  },

  // Lấy chi tiết kết quả phân tích & Canonical Evidence theo Job ID
  getAnalysisById: async (jobId: string): Promise<AnalysisDetailResponse> => {
    const res = await apiClient.get<unknown>(`/v1/analysis/${jobId}`);
    const parseResult = AnalysisDetailResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new SchemaValidationError(
        `AnalysisDetailResponse validation failed: ${parseResult.error.message}`,
        parseResult.error
      );
    }
    return parseResult.data;
  },

  // Lấy gói bằng chứng mật mã RFC 8785 kèm SHA-256 hash (BẢO TOÀN DỮ LIỆU: Trả về CanonicalEvidenceResponse)
  getEvidenceById: async (jobId: string): Promise<CanonicalEvidenceResponse> => {
    const res = await apiClient.get<unknown>(`/v1/analysis/${jobId}/evidence`);
    const parseResult = CanonicalEvidenceResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new SchemaValidationError(
        `CanonicalEvidenceResponse validation failed: ${parseResult.error.message}`,
        parseResult.error
      );
    }
    return parseResult.data;
  },

  // Lấy danh sách lịch sử phân tích có phân trang và lọc (tự động ánh xạ page -> offset)
  listAnalyses: async (params?: AnalysisClientFilterState | AnalysisServerQueryParams): Promise<AnalysisListResponse> => {
    const queryParams = params && 'page' in params ? toAnalysisQueryParams(params) : params;
    const res = await apiClient.get<unknown>('/v1/analysis', { params: queryParams });
    const parseResult = AnalysisListResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new SchemaValidationError(
        `AnalysisListResponse validation failed: ${parseResult.error.message}`,
        parseResult.error
      );
    }
    return parseResult.data;
  },
};
```

#### 3.2. `alertService` (Quản Lý & Tác Chiến Cảnh Báo SOC)
Tệp nguồn: `src/lib/api/alert-service.ts`

> [!WARNING] **BẤT BIẾN AN NINH DỮ LIỆU ĐIỀU TRA (GAP-15)**
> Backend `PATCH /v1/alerts/{alert_id}` chỉ chấp nhận duy nhất trường `{ status: string }`.
> Ghi chú điều tra SOC (`investigation_notes`) và lý do đóng cảnh báo (`dismissal_reason`) TUYỆT ĐỐI KHÔNG lưu vào `localStorage` không mã hóa (nguy cơ rò rỉ dữ liệu điều tra nhạy cảm trên máy tính dùng chung). Dữ liệu này chỉ được duy trì trong In-Memory State (React/Zustand) trong phiên tác chiến của Analyst.

```typescript
import { apiClient } from './client';
import { 
  AlertSummary, 
  AlertSummarySchema,
  AlertListResponse, 
  AlertListResponseSchema,
  AlertStatusUpdateRequest, 
  AlertStatusUpdateRequestSchema,
  AlertQueryParams,
  AlertClientFilterState 
} from '@/types/alert';

export const alertService = {
  // Lấy danh sách cảnh báo đe dọa SOC (GET /v1/alerts)
  listAlerts: async (params?: AlertClientFilterState | AlertQueryParams): Promise<AlertListResponse> => {
    let queryParams: any = params;
    if (params && 'page' in params) {
      queryParams = {
        limit: params.limit,
        offset: Math.max(0, (params.page - 1) * params.limit),
        severity: params.severity,
        status: params.status,
        analysis_job_id: params.analysis_job_id,
      };
    }
    const res = await apiClient.get<unknown>('/v1/alerts', { params: queryParams });
    const parseResult = AlertListResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`AlertListResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },

  // Lấy chi tiết cảnh báo theo ID (GET /v1/alerts/{alert_id})
  getAlertById: async (alertId: string): Promise<AlertSummary> => {
    const res = await apiClient.get<unknown>(`/v1/alerts/${alertId}`);
    const parseResult = AlertSummarySchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`AlertSummary validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },

  // Cập nhật trạng thái vòng đời cảnh báo (PATCH /v1/alerts/{alert_id})
  // BẤT BIẾN BACKEND: Chỉ gửi { status: string }
  updateAlert: async (alertId: string, payload: AlertStatusUpdateRequest): Promise<AlertSummary> => {
    const validPayload = AlertStatusUpdateRequestSchema.parse(payload);
    const res = await apiClient.patch<unknown>(`/v1/alerts/${alertId}`, validPayload);
    const parseResult = AlertSummarySchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`AlertSummary validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },
};
```

#### 3.3. `aiService` (Khuyến Nghị Cố Vấn Jev AI)
Tệp nguồn: `src/lib/api/ai-service.ts`

```typescript
import { apiClient } from './client';
import { 
  JevExplainRequest, 
  JevExplainRequestSchema,
  JevAIRunResponse, 
  JevAIRunResponseSchema,
  JevAIRunListResponse, 
  JevAIRunListResponseSchema,
  JevFeedbackRequest,
  JevFeedbackRequestSchema,
  JevFeedbackResponse,
  JevFeedbackResponseSchema,
  JevFeedbackListResponse,
  JevFeedbackListResponseSchema
} from '@/types/ai';

export const aiService = {
  // Khởi chạy phân tích suy luận cố vấn Jev AI cho Job ID (POST /v1/ai/explain)
  explainJob: async (payload: JevExplainRequest): Promise<JevAIRunResponse> => {
    const validPayload = JevExplainRequestSchema.parse(payload);
    const res = await apiClient.post<unknown>('/v1/ai/explain', validPayload);
    const parseResult = JevAIRunResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`JevAIRunResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },

  // Lấy lịch sử các phiên cố vấn AI (GET /v1/ai/runs)
  listRuns: async (params?: { 
    limit?: number; 
    offset?: number; 
    analysis_id?: string; 
    mode?: string; 
    status?: string 
  }): Promise<JevAIRunListResponse> => {
    const res = await apiClient.get<unknown>('/v1/ai/runs', { params });
    const parseResult = JevAIRunListResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`JevAIRunListResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },

  // Lấy chi tiết một phiên cố vấn AI theo Run ID (GET /v1/ai/runs/{run_id})
  getRunById: async (runId: string): Promise<JevAIRunResponse> => {
    const res = await apiClient.get<unknown>(`/v1/ai/runs/${runId}`);
    const parseResult = JevAIRunResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`JevAIRunResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },

  // Gửi đánh giá phản hồi chất lượng nhận định AI (POST /v1/ai/runs/{run_id}/feedback)
  submitFeedback: async (runId: string, payload: JevFeedbackRequest): Promise<JevFeedbackResponse> => {
    const validPayload = JevFeedbackRequestSchema.parse(payload);
    const res = await apiClient.post<unknown>(`/v1/ai/runs/${runId}/feedback`, validPayload);
    const parseResult = JevFeedbackResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`JevFeedbackResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },

  // Lấy danh sách phản hồi của một phiên cố vấn (GET /v1/ai/runs/{run_id}/feedback)
  listFeedback: async (runId: string): Promise<JevFeedbackListResponse> => {
    const res = await apiClient.get<unknown>(`/v1/ai/runs/${runId}/feedback`);
    const parseResult = JevFeedbackListResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`JevFeedbackListResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },
};
```

#### 3.4. `systemService` (Authentic Telemetry & Sức Khỏe Node)
Tệp nguồn: `src/lib/api/system-service.ts`

```typescript
import { apiClient } from './client';
import { 
  SystemConfigStatusResponse, 
  SystemConfigStatusResponseSchema,
  AuthenticTelemetryResponse, 
  AuthenticTelemetryResponseSchema,
  HealthCheckResponse,
  HealthCheckResponseSchema,
  ReadinessCheckResponse,
  ReadinessCheckResponseSchema
} from '@/types/system';

export const systemService = {
  // Liveness Probe kiểm tra tiến trình hoạt động
  getHealth: async (): Promise<HealthCheckResponse> => {
    const res = await apiClient.get<unknown>('/health');
    const parseResult = HealthCheckResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`HealthCheckResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },

  // Readiness Probe kiểm tra CSDL và Model sẵn sàng
  getReady: async (): Promise<ReadinessCheckResponse> => {
    const res = await apiClient.get<unknown>('/ready');
    const parseResult = ReadinessCheckResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`ReadinessCheckResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },

  // Lấy trạng thái cấu hình hệ thống & thông tin phiên vai trò hiện tại
  getConfigStatus: async (): Promise<SystemConfigStatusResponse> => {
    const res = await apiClient.get<unknown>('/v1/config/status');
    const parseResult = SystemConfigStatusResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`SystemConfigStatusResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },

  // Lấy thông số phần cứng thực tế từ thư viện psutil
  getTelemetry: async (): Promise<AuthenticTelemetryResponse> => {
    const res = await apiClient.get<unknown>('/v1/system/telemetry');
    const parseResult = AuthenticTelemetryResponseSchema.safeParse(res.data);
    if (!parseResult.success) {
      throw new Error(`AuthenticTelemetryResponse validation failed: ${parseResult.error.message}`);
    }
    return parseResult.data;
  },
};
```

#### 3.5. `evaluationService` (Benchmark & Đánh Giá AI) [STATUS: BACKEND_GAP / DESIGN_ONLY]
Tệp nguồn: `src/lib/api/evaluation-service.ts`

> [!NOTE]
> Backend hiện chưa có HTTP endpoints cho `/v1/evaluate`. Động cơ benchmark vận hành ngoại tuyến qua CLI script ghi trực tiếp vào `experiment_runs`. Service này được khai báo ở chế độ Mock / Design Only cho tới khi Backend triển khai API.

```typescript
import { BenchmarkReport, RunBenchmarkPayload } from '@/types/evaluation';
// Dữ liệu mock tĩnh trích xuất từ kết quả chạy CLI offline (run_evaluation.py / artifacts/evaluation/)
import evaluationMockData from '@/mocks/data/evaluation_mock_data.json';

export const evaluationService = {
  // Lấy báo cáo benchmark gần nhất [STATUS: DESIGN_ONLY / BACKEND_GAP]
  getLatestReport: async (): Promise<BenchmarkReport> => {
    // Backend V3 không mở HTTP endpoint /v1/evaluate; nạp dữ liệu snapshot từ CLI offline
    return Promise.resolve(evaluationMockData as BenchmarkReport);
  },

  // Khởi chạy tác vụ đánh giá benchmark mới [STATUS: DESIGN_ONLY / BACKEND_GAP]
  runBenchmark: async (payload: RunBenchmarkPayload): Promise<BenchmarkReport> => {
    // Không gửi HTTP request; mô phỏng độ trễ chạy offline và trả về kết quả benchmark
    await new Promise((resolve) => setTimeout(resolve, 800));
    return Promise.resolve({
      ...evaluationMockData,
      threshold: payload.threshold,
      evaluated_at: new Date().toISOString(),
    } as BenchmarkReport);
  },
};
```

---

### 4. TÍCH HỢP TANSTACK QUERY (REACT QUERY v5) & CƠ CHẾ BỘ NHỚ ĐỆM (CACHING STRATEGY)

#### 4.1. Factory Khóa Truy Vấn Toàn Cục (`queryKeys`)
Tệp nguồn: `src/lib/api/query-keys.ts`

```typescript
export const queryKeys = {
  analysis: {
    all: ['analysis'] as const,
    lists: () => [...queryKeys.analysis.all, 'list'] as const,
    list: (params?: Record<string, any>) => [...queryKeys.analysis.lists(), params] as const,
    details: () => [...queryKeys.analysis.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.analysis.details(), id] as const,
    status: (id: string) => [...queryKeys.analysis.all, 'status', id] as const,
  },
  ai: {
    all: ['ai'] as const,
    advisory: (jobId: string) => [...queryKeys.ai.all, 'advisory', jobId] as const,
  },
  alerts: {
    all: ['alerts'] as const,
    lists: () => [...queryKeys.alerts.all, 'list'] as const,
    list: (params?: Record<string, any>) => [...queryKeys.alerts.lists(), params] as const,
    detail: (id: string) => [...queryKeys.alerts.all, 'detail', id] as const,
  },
  system: {
    health: ['system', 'health'] as const,
    ready: ['system', 'ready'] as const,
    configStatus: ['system', 'config-status'] as const,
    telemetry: ['system', 'telemetry'] as const,
  },
  evaluation: {
    report: ['evaluation', 'report'] as const,
  },
};
```

#### 4.2. Thời Gian Hiệu Lực Dữ Liệu (Stale Times & Cache Times)
- **Canonical Analysis Detail:** `staleTime = Infinity` (Bằng chứng Canonical có mã băm `evidence_hash` là dữ liệu bất biến không bao giờ thay đổi, không cần fetch lại).
- **System Telemetry:** `staleTime = 5000` (5 giây), tự động làm mới nền (`refetchInterval = 10000`).
- **Alert Center:** `staleTime = 15000` (15 giây), tự động làm mới nền để nắm bắt cảnh báo SOC mới.
- **History List:** `staleTime = 30000` (30 giây).

#### 4.3. Quản Lý Trạng Thái Chi Tiết Phân Tích (Analysis Detail State Management)
> [!IMPORTANT]
> **BẤT BIẾN ĐỒNG BỘ:** Phân tích vector qua `POST /v1/analyze/vector` là tác vụ **đồng bộ hoàn toàn** trong backend. Kết quả phán quyết và điểm số M1-M5 được trả về ngay trong HTTP response, frontend chuyển hướng ngay sang `/analysis/{id}` mà không cần bất kỳ cơ chế polling trạng thái trung gian nào.
> Custom hook `useAnalysisDetail` dưới đây đóng vai trò truy vấn dữ liệu chi tiết kèm caching tối ưu:

```typescript
import { useQuery } from '@tanstack/react-query';
import { analysisService } from '@/lib/api/analysis-service';
import { queryKeys } from '@/lib/api/query-keys';

export function useAnalysisDetail(jobId: string) {
  return useQuery({
    queryKey: queryKeys.analysis.detail(jobId),
    queryFn: () => analysisService.getAnalysisById(jobId),
    enabled: !!jobId,
    // Bản ghi Canonical Evidence là bất biến, dữ liệu sau khi tải không bao giờ bị biến đổi
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
}
```

#### 4.4. Cập Nhật Lạc Quan (Optimistic Updates) Cho Trạng Thái Cảnh Báo
Tệp nguồn: `src/hooks/use-update-alert.ts`

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { alertService } from '@/lib/api/alert-service';
import { queryKeys } from '@/lib/api/query-keys';
import { AlertItem, AlertUpdatePayload } from '@/types/alert';
import { toast } from '@/components/feedback/toast';

export function useUpdateAlert(alertId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: AlertUpdatePayload) => alertService.updateAlert(alertId, payload),
    onMutate: async (newPayload) => {
      // Hủy bỏ các refetch đang chạy để không ghi đè dữ liệu lạc quan
      await queryClient.cancelQueries({ queryKey: queryKeys.alerts.detail(alertId) });

      // Lưu snapshot trạng thái cũ để rollback nếu lỗi
      const previousAlert = queryClient.getQueryData<AlertItem>(queryKeys.alerts.detail(alertId));

      // Cập nhật ngay lập tức giao diện người dùng
      if (previousAlert) {
        queryClient.setQueryData<AlertItem>(queryKeys.alerts.detail(alertId), {
          ...previousAlert,
          ...newPayload,
        });
      }

      return { previousAlert };
    },
    onError: (err, newPayload, context) => {
      // Rollback dữ liệu nếu gọi API thất bại
      if (context?.previousAlert) {
        queryClient.setQueryData(queryKeys.alerts.detail(alertId), context.previousAlert);
      }
      toast.error('Cập nhật trạng thái cảnh báo thất bại. Đã khôi phục dữ liệu ban đầu.');
    },
    onSettled: () => {
      // Đồng bộ lại với dữ liệu máy chủ
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.detail(alertId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.lists() });
    },
  });
}
```
