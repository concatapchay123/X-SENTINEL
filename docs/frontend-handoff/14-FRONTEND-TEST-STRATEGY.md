# 14 — CHIẾN LƯỢC KIỂM THỬ TOÀN DIỆN FRONTEND (FRONTEND TEST STRATEGY)
## HỆ THỐNG X-SENTINEL V3 — MALWARE ANALYSIS & THREAT DETECTION PLATFORM

---

### MỤC LỤC
1. [Kim Tự Tháp Kiểm Thử 4 Tầng (4-Layer Testing Pyramid)](#1-kim-tự-tháp-kiểm-thử-4-tầng-4-layer-testing-pyramid)
2. [Chiến Lược Tích Hợp Mock Service Worker (MSW v2 Contract Mocks)](#2-chiến-lược-tích-hợp-mock-service-worker-msw-v2-contract-mocks)
   - [2.1. Cấu Hình Bộ Xử Lý Yêu Cầu Mock Cốt Lõi (Core Prototype MSW Handlers)](#21-cấu-hình-bộ-xử-lý-yêu-cầu-mock-cốt-lõi-core-prototype-msw-handlers)
   - [2.2. Giả Lập Các Trường Hợp Lỗi Biên (Edge Cases & Chaos Simulation)](#22-giả-lập-các-trường-hợp-lỗi-biên-edge-cases--chaos-simulation)
3. [Kịch Bản Kiểm Thử Luồng Người Dùng E2E (Playwright Test Suites)](#3-kịch-bản-kiểm-thử-luồng-người-dùng-e2e-playwright-test-suites)
   - [E2E-01: Luồng Nộp Phân Tích Mẫu & Đối Soát Bằng Chứng Canonical](#e2e-01-luồng-nộp-phân-tích-mẫu--đối-soát-bằng-chứng-canonical)
   - [E2E-02: Luồng Tác Chiến Điều Tra Cảnh Báo SOC & Đóng Sự Cố](#e2e-02-luồng-tác-chiến-điều-tra-cảnh-báo-soc--đóng-sự-cố)
   - [E2E-03: Kiểm Thử Phòng Thủ BOLA/IDOR Chống Truy Cập Chéo Dữ Liệu](#e2e-03-kiểm-thử-phòng-thủ-boidor-chống-truy-cập-chéo-dữ-liệu)
   - [E2E-04: Kiểm Thử Khóa An Toàn Tệp PE Thô (HTTP 501 Fail-Closed)](#e2e-04-kiểm-thử-khóa-an-toàn-tệp-pe-thô-http-501-fail-closed)
   - [E2E-05: Kiểm Thử Viễn Trắc Hạ Tầng Authentic Telemetry `psutil`](#e2e-05-kiểm-thử-viễn-trắc-hạ-tầng-authentic-telemetry-psutil)
4. [Kế Hoạch Kiểm Toán Trợ Năng (Accessibility - a11y) & Hiệu Năng](#4-kế-hoạch-kiểm-toán-trợ-năng-accessibility---a11y--hiệu-năng)

---

### 1. KIM TỰ THÁP KIỂM THỬ 4 TẦNG (4-LAYER TESTING PYRAMID)

Nhằm đảm bảo giao diện Frontend vận hành ổn định trong môi trường tác chiến an ninh mạng với độ tin cậy tuyệt đối, chiến lược kiểm thử của X-SENTINEL V3 được cấu trúc theo 4 tầng phòng ngự:

```
                  / \
                 /   \
                / E2E \       Tầng 4: Playwright E2E User Journeys (5 kịch bản cốt lõi)
               /-------\
              /  a11y   \     Tầng 3: axe-core + WCAG 2.1 AA Accessibility Checks
             /-----------\
            / Integration \   Tầng 2: MSW v2 + React Testing Library (API Boundary)
           /---------------\
          /   Unit Tests    \ Tầng 1: Vitest (Hooks, Zod Schemas, Utils, Atoms)
         /-------------------\
```

| Tầng Kiểm Thử | Công Cụ Chính | Phạm Vi Kiểm Thử | Mục Tiêu Độ Phủ (Coverage) |
|:---|:---|:---|:---|
| **Tầng 1: Unit Tests** | Vitest | Zod Schemas, hàm tiện ích định dạng, trạng thái nút, hook tính toán | $\ge 90\%$ logic code |
| **Tầng 2: Integration Tests** | Vitest + RTL + MSW v2 | Tương tác form, bộ lọc bảng, cơ chế polling, chuyển tab | $\ge 80\%$ components |
| **Tầng 3: a11y Tests** | Playwright + `@axe-core/playwright` | Tương phản màu sắc, điều hướng bàn phím, nhãn ARIA | $100\%$ trang không có lỗi Critical |
| **Tầng 4: E2E Tests** | Playwright (Chromium/Firefox) | Toàn bộ 5 luồng nghiệp vụ liên trang xuyên suốt | $100\%$ luồng nghiệp vụ chính |

---

### 2. CHIẾN LƯỢC TÍCH HỢP MOCK SERVICE WORKER (MSW v2 CONTRACT MOCKS)

MSW v2 được tích hợp để chặn (intercept) toàn bộ các cuộc gọi API mạng ở tầng Service Worker trình duyệt hoặc tầng Node.js trong môi trường test, cho phép đội ngũ Frontend phát triển và kiểm thử độc lập mà không phụ thuộc vào trạng thái uptime của Backend.

#### 2.1. Cấu Hình Bộ Xử Lý Yêu Cầu Mock Cốt Lõi (Core Prototype MSW Handlers)
Tệp nguồn: `src/mocks/handlers.ts`

```typescript
import { http, HttpResponse, delay } from 'msw';
import { DecisionVerdict, JobStatus, AlertSeverity, AlertStatus } from '@/types/enums';
import { VectorAnalysisRequestSchema } from '@/types/analysis';

export const handlers = [
  // 1. POST /v1/analyze/vector (Nộp phân tích vector 2.381 chiều - Xử lý đồng bộ, runtime validation)
  http.post('http://localhost:8000/v1/analyze/vector', async ({ request }) => {
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return HttpResponse.json(
        { 
          detail: { 
            code: 'XS_INPUT_INVALID', 
            message: 'Payload JSON không hợp lệ hoặc bị lỗi cú pháp' 
          } 
        },
        { status: 422 }
      );
    }
    const parseResult = VectorAnalysisRequestSchema.safeParse(body);
    if (!parseResult.success) {
      return HttpResponse.json(
        { 
          detail: { 
            code: 'XS_INPUT_INVALID', 
            message: 'Feature Vector phải đủ 2.381 phần tử số thực hữu hạn',
            errors: parseResult.error.errors 
          } 
        },
        { status: 422 }
      );
    }
    await delay(100);
    return HttpResponse.json({
      request_id: 'req-94a20f51-789a',
      job_id: '94a20f51-789a-4e2a-89a1-0984cfb78912',
      status: 'completed',
      demo_mode: false,
      malware_score: 0.987,
      signals: { m1: 0.992, m2: 0.884, m3: 0.941, m4: 0.760, m5: 0.812 },
      suspicion_score: 0.965,
      threshold: 0.50,
      decision: DecisionVerdict.QUARANTINE,
      view_contributions: { structural: 0.35, behavioral: 0.45, metadata: 0.20 },
      warnings: [],
      evidence_ref: '994e7f813be6702d9d4def0d93edc47ff4dc1fd5249af19e65768d106a59594e',
    });
  }),

  // 2. GET /v1/analysis/:id (Chi tiết Bằng chứng Canonical & Điểm M1-M5)
  http.get('http://localhost:8000/v1/analysis/:id', async ({ params, request }) => {
    const authHeader = request.headers.get('Authorization');
    // Kiểm tra bảo vệ BOLA: token-analyst-2 cố tình xem job của token-analyst
    if (authHeader?.includes('token-analyst-2')) {
      return HttpResponse.json(
        { detail: { code: 'XS_FORBIDDEN', message: 'Access denied: resource belongs to another user' } },
        { status: 403 }
      );
    }

    await delay(80);
    return HttpResponse.json({
      id: params.id,
      request_id: 'req-94a20f51-789a',
      status: JobStatus.COMPLETED,
      input_mode: 'vector',
      demo_mode: false,
      result: {
        decision: 'quarantine',
        malware_score: 0.987,
        suspicion_score: 0.965,
        threshold: 0.50,
        latency_ms: 42,
        view_contributions: { structural: 0.35, behavioral: 0.45, metadata: 0.20 },
      },
      scores: [
        { detector_code: 'M1', score: 0.992, diagnostics: { name: 'TADR' } },
        { detector_code: 'M2', score: 0.884, diagnostics: { name: 'Tabular STRIP' } },
        { detector_code: 'M3', score: 0.941, diagnostics: { name: 'View Concentration' } },
        { detector_code: 'M4', score: 0.760, diagnostics: { name: 'Cross-View Disagreement' } },
        { detector_code: 'M5', score: 0.812, diagnostics: { name: 'Semantic Plausibility' } },
      ],
      evidence_ref: '994e7f813be6702d9d4def0d93edc47ff4dc1fd5249af19e65768d106a59594e',
      created_at: new Date(Date.now() - 3600000).toISOString(),
      completed_at: new Date().toISOString(),
    });
  }),

  // 3. POST /v1/ai/explain (Khuyến nghị Cố vấn Jev AI chuẩn Canonical DTO)
  http.post('http://localhost:8000/v1/ai/explain', async () => {
    await delay(200);
    return HttpResponse.json({
      id: '7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d',
      analysis_job_id: '94a20f51-789a-4e2a-89a1-0984cfb78912',
      requested_by_user_id: '22222222-2222-2222-2222-222222222222',
      mode: 'explain',
      status: 'completed',
      advisory_only: true, // BẤT BIẾN: Khẳng định cố vấn, không sửa đổi kết luận kỹ thuật
      authoritative_decision_unchanged: true,
      model_id: 'Jev-Style-Qwen3.5-2B-Decision',
      endpoint_label: 'lm_studio_local',
      prompt_version: 'jev-v3.0.0',
      input_digest_sha256: '41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb',
      output_digest_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      context_summary: { decision_result: { verdict: 'ALERT', confidence: 0.85 } },
      response_text: 'Mẫu PE có dấu hiệu tiêm mã độc vào tiến trình thông qua API VirtualAllocEx.',
      decision_result: { verdict: 'ALERT', confidence: 0.85 },
      latency_ms: 184.2,
      error_code: null,
      error_message: null,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    });
  }),

  // 4. POST /v1/analyze/file (Gated 501 Disabled Endpoint)
  http.post('http://localhost:8000/v1/analyze/file', async () => {
    return HttpResponse.json(
      { detail: { code: 'XS_FEATURE_DISABLED', message: 'Nộp tệp nhị phân thô tạm thời vô hiệu hóa' } },
      { status: 501 }
    );
  }),

  // 5. GET /v1/system/telemetry (Authentic psutil Hardware Metrics)
  http.get('http://localhost:8000/v1/system/telemetry', async () => {
    return HttpResponse.json({
      status: 'ok',
      cpu: {
        utilization_percent: 14.8,
        logical_cores: 8,
        physical_cores: 8,
      },
      memory: {
        total_bytes: 17098485760,
        available_bytes: 8452145152,
        used_bytes: 8646340608,
        used_percent: 50.6,
      },
      process: {
        pid: 14220,
        rss_bytes: 220012544,
        vms_bytes: 654215168,
        thread_count: 12,
      },
    });
  }),

  // 6. GET /v1/alerts (Danh sách cảnh báo SOC chuẩn DTO)
  http.get('http://localhost:8000/v1/alerts', async () => {
    return HttpResponse.json({
      items: [
        {
          id: 'e4f5a6b7-8901-2345-6789-abcdef012345',
          analysis_job_id: '94a20f51-789a-4e2a-89a1-0984cfb78912',
          severity: 'high',
          status: 'open',
          reason: 'M4 Cross-View discrepancy detected potential evasion trigger',
          created_at: new Date(Date.now() - 3600000).toISOString(),
          resolved_at: null,
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
  }),

  // 7. GET /v1/ai/runs (Danh sách lượt chạy Jev AI)
  http.get('http://localhost:8000/v1/ai/runs', async () => {
    return HttpResponse.json({
      items: [
        {
          id: '7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d',
          analysis_job_id: '94a20f51-789a-4e2a-89a1-0984cfb78912',
          requested_by_user_id: '22222222-2222-2222-2222-222222222222',
          mode: 'explain',
          status: 'completed',
          advisory_only: true,
          authoritative_decision_unchanged: true,
          model_id: 'Jev-Style-Qwen3.5-2B-Decision',
          endpoint_label: 'lm_studio_local',
          prompt_version: 'jev-v3.0.0',
          input_digest_sha256: '41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb',
          output_digest_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          context_summary: { decision_result: { verdict: 'ALERT', confidence: 0.85 } },
          response_text: 'Mẫu PE có dấu hiệu tiêm mã độc vào tiến trình thông qua API VirtualAllocEx.',
          decision_result: { verdict: 'ALERT', confidence: 0.85 },
          latency_ms: 184.2,
          error_code: null,
          error_message: null,
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
  }),
];
```

#### 2.2. Giả Lập Các Trường Hợp Lỗi Biên (Edge Cases & Chaos Simulation)
MSW cung cấp các handler động hỗ trợ kiểm thử giao diện trong điều kiện mạng khắc nghiệt:
1. **Mô phỏng Quá tải Detector (HTTP 429 `XS_DETECTOR_OVERLOADED`):** Kiểm tra xem Countdown Toast có tự động hiển thị đếm ngược 5 giây hay không.
2. **Mô phỏng Đứt kết nối AI Engine (HTTP 503 `XS_AI_UNAVAILABLE`):** Đảm bảo trang Canonical Evidence tại `/analysis/{id}` vẫn hiển thị bình thường, chỉ riêng tab Jev AI báo trạng thái Degraded.

#### 2.3. Kiểm Thử Tính Toàn Vẹn Bằng Chứng Mật Mã 3 Tầng (3-Level SHA-256 Evidence Verification Suite)
Tệp nguồn: `src/tests/evidence-verification.test.ts` (Vitest / Node Test Runner)

Bộ kiểm thử này thực thi phân cấp 3 tầng nghiêm ngặt (3-Level Verification Contract) bảo đảm tính toàn vẹn tuyệt đối của dữ liệu bằng chứng pháp chứng:

```typescript
import { describe, it, expect } from 'vitest';
import crypto from 'crypto';
import { CanonicalEvidenceResponseSchema, type CanonicalEvidenceResponse } from '@/types/analysis';

// Hàm tính mã băm chuẩn mực RFC 8785 (JCS) độc lập tại tầng Frontend
export function computeCanonicalEvidenceHash(evidence: Record<string, any>): string {
  const canonical19: Record<string, any> = {
    build_digest: evidence.build_digest,
    code_commit: evidence.code_commit,
    decision: evidence.decision,
    demo_mode: evidence.demo_mode,
    detector_config_hash: evidence.detector_config_hash,
    fusion_score: Number(evidence.fusion_score),
    input_id: evidence.input_id,
    input_mode: evidence.input_mode,
    latency_ms: Object.keys(evidence.latency_ms || {})
      .sort()
      .reduce((acc: any, k) => {
        acc[k] = Number(evidence.latency_ms[k]);
        return acc;
      }, {}),
    malware_score: Number(evidence.malware_score),
    model_config_hash: evidence.model_config_hash,
    model_hash: evidence.model_hash,
    request_id: evidence.request_id,
    run_id: evidence.run_id,
    seed: Number(evidence.seed),
    signals: Object.keys(evidence.signals || {})
      .sort()
      .reduce((acc: any, k) => {
        acc[k] = Number(evidence.signals[k]);
        return acc;
      }, {}),
    threshold_id: evidence.threshold_id,
    timestamp: evidence.timestamp,
    view_map_hash: evidence.view_map_hash,
  };

  const sortedKeys = Object.keys(canonical19).sort();
  const canonicalSorted: Record<string, any> = {};
  for (const k of sortedKeys) {
    canonicalSorted[k] = canonical19[k];
  }
  const canonicalJson = JSON.stringify(canonicalSorted);
  return crypto.createHash('sha256').update(canonicalJson, 'utf8').digest('hex');
}

describe('3-Level Canonical Evidence Verification Contract', () => {
  const goldenEvidenceFixture: CanonicalEvidenceResponse = {
    request_id: 'REQ-2026-TEST-001',
    run_id: 'RUN-2026-TEST-A1',
    timestamp: '2026-10-12T14:30:00.000000+00:00',
    code_commit: 'c0ffee1234567890abcdef1234567890abcdef12',
    build_digest: 'sha256:11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff',
    input_id: 'sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
    input_mode: 'vector',
    view_map_hash: '276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb',
    model_hash: '509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2',
    model_config_hash: 'a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123',
    detector_config_hash: 'b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1',
    seed: 42,
    malware_score: 0.825,
    signals: { m1: 0.12, m2: 0.34, m3: 0.56, m4: 0.78, m5: 0.90 },
    fusion_score: 0.654,
    threshold_id: 'THRESH-D1-OPT-0.50',
    decision: 'ALERT',
    latency_ms: { end_to_end: 7.42, fusion: 0.8, m1: 1.2 },
    demo_mode: false,
    evidence_hash: 'a7edb1d3990f331ecf1b6c266f0af7d536593f9711a58c312e58e6f233b9f54d',
    verified: true,
  };

  // LEVEL 1: UI DISPLAY SMOKE TEST
  it('Level 1: UI Display Smoke Test xác minh chuỗi hex 64 ký tự hợp lệ và không dùng chuỗi rỗng hash', () => {
    const hash = goldenEvidenceFixture.evidence_hash;
    expect(hash).toBeDefined();
    expect(hash.length).toBe(64);
    expect(/^[a-f0-9]{64}$/.test(hash)).toBe(true);
    // Bác bỏ chuỗi rỗng sha256 e3b0c442...
    expect(hash).not.toContain('e3b0c442');
  });

  // LEVEL 2: RESPONSE CONTRACT TEST
  it('Level 2: Response Contract Test xác thực đầy đủ 19 trường canonical và cấu trúc envelope', () => {
    const parseResult = CanonicalEvidenceResponseSchema.safeParse(goldenEvidenceFixture);
    expect(parseResult.success).toBe(true);

    // Negative case: Hash sai độ dài (63 hoặc 65 ký tự)
    const invalidLenFixture = { ...goldenEvidenceFixture, evidence_hash: 'a'.repeat(63) };
    expect(CanonicalEvidenceResponseSchema.safeParse(invalidLenFixture).success).toBe(false);

    // Negative case: Hash chứa ký tự non-hex
    const nonHexFixture = { ...goldenEvidenceFixture, evidence_hash: 'g'.repeat(64) };
    expect(CanonicalEvidenceResponseSchema.safeParse(nonHexFixture).success).toBe(false);

    // Negative case: Thiếu trường bắt buộc trong 19 trường canonical
    const missingFieldFixture = { ...goldenEvidenceFixture } as any;
    delete missingFieldFixture.code_commit;
    expect(CanonicalEvidenceResponseSchema.safeParse(missingFieldFixture).success).toBe(false);
  });

  // LEVEL 3: CRYPTOGRAPHIC INTEGRITY TEST
  it('Level 3: Cryptographic Integrity Test tính lại SHA-256 từ 19 trường canonical và so khớp chính xác với Backend', () => {
    const recomputedHash = computeCanonicalEvidenceHash(goldenEvidenceFixture);
    // Mã băm tính lại độc lập tại Frontend phải khớp 100% với Backend
    expect(recomputedHash).toBe('a7edb1d3990f331ecf1b6c266f0af7d536593f9711a58c312e58e6f233b9f54d');
    expect(recomputedHash).toBe(goldenEvidenceFixture.evidence_hash);

    // Tampered case: Payload bị sửa đổi điểm số -> mã băm tính lại không khớp
    const tamperedPayload = { ...goldenEvidenceFixture, malware_score: 0.100 };
    const tamperedRecomputed = computeCanonicalEvidenceHash(tamperedPayload);
    expect(tamperedRecomputed).not.toBe(goldenEvidenceFixture.evidence_hash);

    // Tampered digest: Kẻ tấn công sửa evidence_hash giả lập
    const forgedHash = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff';
    const isIntegrityValid = computeCanonicalEvidenceHash(goldenEvidenceFixture) === forgedHash;
    expect(isIntegrityValid).toBe(false);
  });
});
```

---

### 3. KỊCH BẢN KIỂM THỬ LUỒNG NGƯỜI DÙNG E2E (PLAYWRIGHT TEST SUITES)

#### E2E-01: LUỒNG NỘP PHÂN TÍCH MẪU & ĐỐI SOÁT BẰNG CHỨNG CANONICAL
Tệp nguồn: `e2e/malware-analysis.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Luồng Nộp Mẫu & Xem Canonical Evidence', () => {
  test('Nộp vector 2.381 chiều, xử lý đồng bộ và kiểm tra Hero Verdict Card', async ({ page }) => {
    // 1. Truy cập trang Nộp mẫu
    await page.goto('/analyze');
    await expect(page.locator('h1')).toContainText('Trang Nộp Mẫu Phân Tích Mã Độc PE');

    // 2. Nhấn nút nạp dữ liệu mẫu Ransomware
    await page.getByRole('button', { name: 'Nạp Mẫu Ransomware (WannaCry)' }).click();

    // 3. Kiểm tra form báo hợp lệ (2.381/2.381 phần tử)
    await expect(page.locator('text=Độ dài hiện tại: 2.381/2.381 phần tử')).toBeVisible();

    // 4. Bấm nút Tiến hành phân tích
    await page.getByRole('button', { name: 'TIẾN HÀNH PHÂN TÍCH MẪU (RUN)' }).click();

    // 5. Kiểm tra tự động chuyển trang sang /analysis/:id
    await page.waitForURL(/\/analysis\/[0-9a-f-]+/);

    // 6. Xác minh Hero Verdict Card hiển thị đúng phán quyết QUARANTINE
    const verdictHero = page.locator('[data-testid="hero-verdict-card"]');
    await expect(verdictHero).toBeVisible();
    await expect(verdictHero).toContainText('QUARANTINE');

    // 7. Xác minh mã băm bằng chứng SHA-256 (3-Level Verification Contract):
    // Level 1: Định dạng chuẩn 64 ký tự hex hợp lệ theo biểu thức chính quy /^[a-f0-9]{64}$/
    // Level 2: Khớp với tiền tố mã băm golden reference RFC 8785 của backend (994e7f81...)
    // Level 3: Bác bỏ hoàn toàn chuỗi rỗng hash e3b0c442...
    const hashBlock = page.locator('[data-testid="evidence-hash-block"]');
    await expect(hashBlock).toBeVisible();
    await expect(hashBlock).toHaveText(/^[a-f0-9]{64}$/);
    await expect(hashBlock).toContainText('994e7f81');

    // 8. Chuyển sang tab Giải trình SHAP (P03)
    await page.getByRole('tab', { name: 'Giải trình Mô hình' }).click();
    await expect(page.locator('[data-testid="shap-waterfall-chart"]')).toBeVisible();

    // 9. Chuyển sang tab Khuyến nghị Jev AI (P04) và kiểm tra Banner Cảnh báo bắt buộc
    await page.getByRole('tab', { name: 'Cố vấn Bảo mật Jev AI' }).click();
    const advisoryBanner = page.locator('text=KHUYẾN NGHỊ THAM KHẢO DUY NHẤT (ADVISORY ONLY)');
    await expect(advisoryBanner).toBeVisible();
  });
});
```

#### E2E-02: LUỒNG TÁC CHIẾN ĐIỀU TRA CẢNH BÁO SOC & ĐÓNG SỰ CỐ
Tệp nguồn: `e2e/soc-triage.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Luồng Điều Tra Cảnh Báo SOC', () => {
  test('Lọc cảnh báo Critical, mở điều tra và đóng cảnh báo kèm ghi chú lý do', async ({ page }) => {
    // 1. Truy cập Trung tâm cảnh báo
    await page.goto('/alerts');
    await expect(page.locator('h1')).toContainText('Trung Tâm Quản Trị Cảnh Báo Đe Dọa SOC');

    // 2. Chọn bộ lọc mức Nghiêm trọng: CRITICAL
    await page.getByRole('button', { name: 'Mức độ: Tất cả' }).click();
    await page.getByRole('option', { name: 'CRITICAL' }).click();

    // 3. Nhấp vào hàng cảnh báo đầu tiên để mở trang điều tra P07
    await page.locator('table tbody tr').first().click();
    await page.waitForURL(/\/alerts\/[0-9a-f-]+/);

    // 4. Xác minh Status Stepper đang ở bước OPEN
    await expect(page.locator('[data-testid="stepper-step-open"]')).toHaveAttribute('data-active', 'true');

    // 5. Chuyển trạng thái sang ACKNOWLEDGED
    await page.getByRole('button', { name: 'Tiếp Nhận Điều Tra' }).click();
    await expect(page.locator('[data-testid="stepper-step-acknowledged"]')).toHaveAttribute('data-active', 'true');

    // 6. Nhấn nút Đóng cảnh báo (Bỏ qua/Dismiss) để mở Dangerous Modal
    await page.getByRole('button', { name: 'Đóng (Báo Động Giả / Dismiss)' }).click();
    const modal = page.locator('[data-testid="dangerous-action-modal"]');
    await expect(modal).toBeVisible();

    // 7. Nhập lý do < 20 ký tự -> nút xác nhận vẫn bị vô hiệu hóa
    const notesInput = modal.locator('textarea');
    await notesInput.fill('Nhầm lẫn nhẹ');
    const confirmBtn = modal.getByRole('button', { name: 'Xác Nhận Đóng Cảnh Báo' });
    await expect(confirmBtn).toBeDisabled();

    // 8. Nhập lý do hợp lệ >= 20 ký tự -> nút xác nhận bật sáng
    await notesInput.fill('Phần mềm kế toán nội bộ được ký số hợp lệ, xác minh là báo động giả.');
    await expect(confirmBtn).toBeEnabled();
    await confirmBtn.click();

    // 9. Modal đóng và trạng thái chuyển sang DISMISSED
    await expect(modal).toBeHidden();
    await expect(page.locator('text=Trạng thái hiện tại: dismissed')).toBeVisible();
  });
});
```

#### E2E-03: KIỂM THỬ PHÒNG THỦ BOLA/IDOR CHỐNG TRUY CẬP CHÉO DỮ LIỆU
Tệp nguồn: `e2e/security-bola.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Kiểm Thử Phòng Thủ BOLA/IDOR', () => {
  test('Chuyên viên phụ (token-analyst-2) không thể xem Job của Chuyên viên chính', async ({ page }) => {
    // 1. Chuyển sang token-analyst-2 tại trang /auth/switch
    await page.goto('/auth/switch');
    await page.getByRole('button', { name: 'Secondary Analyst (token-analyst-2)' }).click();
    await expect(page.locator('text=Vai trò hiện tại: analyst (token-analyst-2)')).toBeVisible();

    // 2. Cố tình truy cập trực tiếp URL Job của chuyên viên khác
    const targetJobId = '94a20f51-789a-4e2a-89a1-0984cfb78912';
    await page.goto(`/analysis/${targetJobId}`);

    // 3. Xác minh xuất hiện màn hình BOLA 403 Forbidden thay vì thông tin phân tích
    const bolaView = page.locator('[data-testid="bola-error-view"]');
    await expect(bolaView).toBeVisible();
    await expect(bolaView).toContainText('Quyền Truy Cập Bị Giới Hạn');
    await expect(page.locator('[data-testid="hero-verdict-card"]')).toBeHidden();
  });
});
```

---

### 4. KẾ HOẠCH KIỂM TOÁN TRỢ NĂNG (ACCESSIBILITY - a11y) & HIỆU NĂNG

1. **Kiểm tra Tự Động Với axe-core:**
   - Mỗi trang trong 10 trang Frontend đều được tích hợp test tự động trong pipeline CI:
     ```typescript
     const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
     expect(accessibilityScanResults.violations).toEqual([]);
     ```
2. **Quy Tắc Độ Tương Phản Màu Sắc (Contrast Ratio):**
   - Mọi văn bản hiển thị trên nền tối `--color-bg-base` (`#121418`) phải có tỷ lệ tương phản tối thiểu $7:1$ (chuẩn WCAG AAA) đối với nội dung chính và $4.5:1$ đối với nhãn phụ.
3. **Kiểm Tra Không Rung Lắc Giao Diện (Layout Stability CLS):**
   - Chỉ số **Cumulative Layout Shift (CLS)** đo đạc qua Lighthouse Audit phải đạt $\mathbf{CLS \le 0.02}$, đảm bảo quá trình chuyển đổi từ Skeleton sang dữ liệu thực không làm giật khung hình.
