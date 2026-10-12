# PLAN-BE-10 — Jev AI LM Studio Runtime Client

## Objective
Implement local OpenAI-compatible client with configurable model/base URL/timeouts.

## Status: PASS

## Scope

- Implement local OpenAI-compatible HTTP client for LM Studio runtime inference (`JevAIClient`).
- Support configurable model ID, base URL, connection/read timeouts, temperature, token limit, and prompt version.
- Enforce strict local-only loopback host boundaries (`localhost`, `127.0.0.1`, `host.docker.internal`) with zero cloud egress.
- Maintain detector science, platform persistence, and Jev AI authority boundaries explicit (advisory-only, zero influence on detector decisions).
- Implement disabled mode guaranteeing exactly zero network calls when disabled.
- Implement explicit timeout and network error mapping preserving caller resilience without crashing detector pipelines.

## Primary files
- `backend/src/x_sentinel/jev_ai/client.py`
- `backend/src/x_sentinel/jev_ai/__init__.py`
- `configs/jev_ai.yaml`
- `backend/tests/test_be10_jev_ai_runtime_client.py`
- `backend/tests/test_jev_ai.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 through BE-09 verified; BE-10 readiness gate passed in `docs/audits/be01_be09_pre_be10/BE10_READINESS_GATE.md`).
2. [x] Freeze interfaces/config/schema for this slice (`JevAIClient`, `JevResponse`, `JevStatusResponse`, `JevAIError`, `JevAIUnavailable`, `JevAIDisabledError`, `JevAIConfigurationError`, `JevAITimeout`, `JevAIConnectionError`, `JevAIHTTPError`, `JevAIResponseError`).
3. [x] Implement runtime client, error hierarchy, lifecycle management, and factory methods (`backend/src/x_sentinel/jev_ai/client.py`, `configs/jev_ai.yaml`, `backend/src/x_sentinel/jev_ai/__init__.py`).
4. [x] Add positive and negative tests (29 comprehensive automated tests in `backend/tests/test_be10_jev_ai_runtime_client.py`).
5. [x] Verify regression across foundational suites (`test_be01_environment_config.py`, `test_be03_foundation_health_readiness.py`, `test_jev_ai.py`, `test_be09_core_api.py`, `test_be09_authorization.py`, `test_be08_canonical_evidence_contract.py`, `test_be07_fusion_engine.py`, `test_be06_m1_m5`).
6. [x] Update traceability/readiness documentation (`PLAN-BE-10.md`).

## Acceptance

### 1. Disabled Mode: PASS
- When `enabled=False` or `XS_JEV_AI_ENABLED=false`:
  - `JevAIClient.chat()` raises `JevAIDisabledError` (subclass of `JevAIUnavailable`).
  - Exactly zero network requests are dispatched to any host or port (verified with mock transport call count == 0).
  - `JevAIClient.probe_models()` returns `[]` immediately with zero network calls.
  - `JevAIClient.check_availability()` returns `False` immediately with zero network calls.
  - Backend startup is completely unaffected.
  - Backend readiness endpoint `GET /ready` returns 200 OK without blocker.
  - AI status endpoint `GET /v1/ai/status` reports `status: "disabled"`, `readiness_blocking: false`.
  - Verified by tests: `test_disabled_mode_zero_network_calls_on_chat`, `test_disabled_mode_zero_network_calls_on_probe_models`, `test_ai_disabled_zero_network_calls`, `test_ai_disabled_api_status_endpoint`, `test_ai_disabled_does_not_block_backend_readiness`, `test_ai_disabled_zero_socket_connections`.

### 2. Mocked Success: PASS
- OpenAI-compatible chat completions runtime contract verified with mock HTTP transport:
  - Correct HTTP POST dispatched to `{base_url}/chat/completions`.
  - Correct model identifier forwarded from configuration.
  - JSON payload formatted with `model`, `messages`, `temperature`, `max_tokens`, `stream=false`.
  - JSON headers `Content-Type: application/json`, `Accept: application/json`.
  - Response parsed cleanly into typed `JevResponse` with `text`, `model_id`, `prompt_version`, `advisory_only=True`, and measured `latency_ms`.
  - `/models` probe endpoint verified with mock transport returning available models list.
  - Verified by tests: `test_mocked_success_chat_completions`, `test_mocked_success_probe_models`, `test_client_reused_across_multiple_requests`.

### 3. Timeout Handling: PASS
- Bounded connect, read, and request timeouts enforced:
  - `httpx.ConnectTimeout` re-raised as `JevAITimeout(timeout_type="connect")`.
  - `httpx.ReadTimeout` re-raised as `JevAITimeout(timeout_type="read")`.
  - `httpx.TimeoutException` re-raised as `JevAITimeout(timeout_type="request")`.
  - `JevAITimeout` inherits from `JevAIUnavailable` for seamless caller compatibility.
  - Client connections released cleanly without leaks.
  - Detector execution and readiness are not blocked or mutated by timeouts.
  - Verified by tests: `test_timeout_connect_raises_jev_ai_timeout`, `test_timeout_read_raises_jev_ai_timeout`.

### 4. Network Failure Handling: PASS
- Explicit network failure classification and containment:
  - Connection refused (`httpx.ConnectError`) re-raised as `JevAIConnectionError`.
  - Transport disconnect (`httpx.RemoteProtocolError`, `httpx.NetworkError`) re-raised as `JevAIConnectionError`.
  - HTTP 5xx server errors re-raised as `JevAIHTTPError` with explicit HTTP `status_code` and truncated body.
  - HTTP 4xx client errors re-raised as `JevAIHTTPError`.
  - Malformed non-JSON payload re-raised as `JevAIResponseError`.
  - Missing/empty `choices` array or missing `message`/`content` re-raised as `JevAIResponseError`.
  - All errors subclass `JevAIUnavailable` and preserve detector/evidence isolation.
  - No fallback to external cloud LLM APIs under any circumstance.
  - Verified by tests: `test_network_connection_refused_raises_connection_error`, `test_network_transport_disconnect_raises_connection_error`, `test_http_500_server_error_raises_jev_ai_http_error`, `test_http_404_not_found_raises_jev_ai_http_error`, `test_response_malformed_json_raises_response_error`, `test_response_missing_choices_raises_response_error`, `test_response_empty_choices_array_raises_response_error`, `test_response_missing_message_or_content_raises_response_error`.

## Extended Verification & Architectural Invariants
- Factory methods: `JevAIClient.from_settings()` and `JevAIClient.from_config()`.
- Lifecycle management: Context manager `with JevAIClient(...) as client:` and explicit `close()` method.
- Security & Guardrails: Strict URL scheme validation (`http`/`https`), host allowlist validation (`localhost`, `127.0.0.1`, `host.docker.internal`), zero secret leakage in logs, zero prompt logging.
- Detector Independence: Formally verified that `DetectorPipeline` and M1–M5 core detectors have zero dependencies on Jev AI.
- Orchestrator Integration: Verified seamless compatibility with `JevAIOrchestrator.run(request)`.

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`PLAN-BE-11` (Jev AI Context Builder & Data Contract).
