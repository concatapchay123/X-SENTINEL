from __future__ import annotations

import json

import httpx
import pytest
from x_sentinel.config import Settings
from x_sentinel.jev_ai.client import (
    JevAIClient,
    JevAIConfigurationError,
    JevAIConnectionError,
    JevAIDisabledError,
    JevAIHTTPError,
    JevAIResponseError,
    JevAITimeout,
    JevAIUnavailable,
)
from x_sentinel.jev_ai.guardrails import JevContextBlocked
from x_sentinel.jev_ai.schemas import JevResponse

# ===========================================================================
# 1. Configuration & Factory Tests
# ===========================================================================


def test_client_init_valid_defaults() -> None:
    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
    )
    assert client.base_url == "http://localhost:1234/v1"
    assert client.model_id == "test-model"
    assert client.enabled is True
    assert client.timeout_seconds == 60.0
    assert client.temperature == 0.1
    assert client.prompt_version == "jev-v3.0.0"
    assert client.endpoint == "http://localhost:1234/v1/chat/completions"
    client.close()


def test_client_init_strips_trailing_slash() -> None:
    client = JevAIClient(
        base_url="http://localhost:1234/v1///",
        model_id="test-model",
    )
    assert client.base_url == "http://localhost:1234/v1"
    assert client.endpoint == "http://localhost:1234/v1/chat/completions"
    client.close()


def test_client_init_rejects_empty_model() -> None:
    with pytest.raises(JevAIConfigurationError):
        JevAIClient(base_url="http://localhost:1234/v1", model_id="")


def test_client_init_rejects_invalid_timeout() -> None:
    with pytest.raises(JevAIConfigurationError):
        JevAIClient(base_url="http://localhost:1234/v1", model_id="m", timeout_seconds=0)

    with pytest.raises(JevAIConfigurationError):
        JevAIClient(base_url="http://localhost:1234/v1", model_id="m", timeout_seconds=-5.0)


def test_client_init_rejects_invalid_temperature() -> None:
    with pytest.raises(JevAIConfigurationError):
        JevAIClient(base_url="http://localhost:1234/v1", model_id="m", temperature=-0.1)

    with pytest.raises(JevAIConfigurationError):
        JevAIClient(base_url="http://localhost:1234/v1", model_id="m", temperature=2.5)


def test_client_init_enforces_local_only() -> None:
    with pytest.raises(JevContextBlocked):
        JevAIClient(
            base_url="https://api.openai.com/v1",
            model_id="m",
            local_only=True,
        )


def test_client_from_settings_factory() -> None:
    mock_settings = Settings(
        jev_ai_enabled=True,
        jev_ai_base_url="http://localhost:1234/v1",
        jev_ai_model="hermes-3-test",
        jev_ai_timeout_seconds=45.0,
        jev_ai_temperature=0.2,
        jev_ai_prompt_version="jev-v3.0.1",
        jev_ai_local_only=True,
    )
    client = JevAIClient.from_settings(settings_obj=mock_settings)
    assert client.enabled is True
    assert client.base_url == "http://localhost:1234/v1"
    assert client.model_id == "hermes-3-test"
    assert client.timeout_seconds == 45.0
    assert client.temperature == 0.2
    assert client.prompt_version == "jev-v3.0.1"
    client.close()


def test_client_from_config_dict_factory() -> None:
    config_dict = {
        "enabled": True,
        "base_url": "http://127.0.0.1:1234/v1",
        "model_id": "custom-lm-studio",
        "request": {
            "timeout_seconds": 30.0,
            "temperature": 0.05,
            "max_output_tokens": 1500,
        },
        "prompt_version": "jev-v3.2.0",
        "security": {
            "local_only": True,
            "allowed_hosts": ["127.0.0.1"],
        },
    }
    client = JevAIClient.from_config(config_dict)
    assert client.enabled is True
    assert client.base_url == "http://127.0.0.1:1234/v1"
    assert client.model_id == "custom-lm-studio"
    assert client.timeout_seconds == 30.0
    assert client.temperature == 0.05
    assert client.max_output_tokens == 1500
    assert client.prompt_version == "jev-v3.2.0"
    client.close()


# ===========================================================================
# 2. Acceptance Criterion 1: Disabled Mode
# ===========================================================================


def test_disabled_mode_zero_network_calls_on_chat() -> None:
    """When client is disabled, calling chat() must raise JevAIDisabledError
    and execute exactly zero network requests."""
    network_dispatched = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal network_dispatched
        network_dispatched = True
        return httpx.Response(200, json={"choices": [{"message": {"content": "leak"}}]})

    mock_transport = httpx.MockTransport(handler)
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        enabled=False,
        http_client=mock_http_client,
    )

    with pytest.raises(JevAIDisabledError) as exc_info:
        client.chat([{"role": "user", "content": "hello"}])

    assert "disabled" in str(exc_info.value).lower()
    assert issubclass(JevAIDisabledError, JevAIUnavailable)
    assert not network_dispatched, "Network call was dispatched when client was disabled!"
    client.close()


def test_disabled_mode_zero_network_calls_on_probe_models() -> None:
    """When client is disabled, probe_models() must return [] with zero network calls."""
    network_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        return httpx.Response(200, json={"data": [{"id": "model-1"}]})

    mock_transport = httpx.MockTransport(handler)
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        enabled=False,
        http_client=mock_http_client,
    )

    models = client.probe_models()
    assert models == []
    assert client.check_availability() is False
    assert network_calls == 0
    client.close()


# ===========================================================================
# 3. Acceptance Criterion 2: Mocked Success
# ===========================================================================


def test_mocked_success_chat_completions() -> None:
    """Test successful OpenAI-compatible chat completion request and response parsing."""
    captured_requests: list[httpx.Request] = []

    mock_openai_response = {
        "id": "chatcmpl-test-12345",
        "object": "chat.completion",
        "created": 1728700000,
        "model": "hermes-3-llama-3.1-8b",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Advisory explanation: Sample exhibits suspicious imports and high entropy in .rsrc section.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 45,
            "total_tokens": 165,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=mock_openai_response)

    mock_transport = httpx.MockTransport(handler)
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="hermes-3-llama-3.1-8b",
        temperature=0.15,
        max_output_tokens=1000,
        prompt_version="jev-v3.0.0",
        http_client=mock_http_client,
    )

    messages = [
        {"role": "system", "content": "You are Jev AI advisory assistant."},
        {"role": "user", "content": "Analyze evidence."},
    ]

    response = client.chat(messages)

    # 1. Verify returned JevResponse
    assert isinstance(response, JevResponse)
    assert response.text == "Advisory explanation: Sample exhibits suspicious imports and high entropy in .rsrc section."
    assert response.model_id == "hermes-3-llama-3.1-8b"
    assert response.prompt_version == "jev-v3.0.0"
    assert response.advisory_only is True
    assert response.latency_ms is not None and response.latency_ms >= 0.0

    # 2. Verify request dispatched to transport
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.method == "POST"
    assert str(req.url) == "http://localhost:1234/v1/chat/completions"
    assert req.headers["content-type"] == "application/json"

    body = json.loads(req.content.decode("utf-8"))
    assert body["model"] == "hermes-3-llama-3.1-8b"
    assert body["temperature"] == 0.15
    assert body["max_tokens"] == 1000
    assert body["stream"] is False
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"

    client.close()


def test_mocked_success_probe_models() -> None:
    """Test successful /models probing on LM Studio."""
    mock_models_response = {
        "data": [
            {"id": "hermes-3-llama-3.1-8b", "object": "model"},
            {"id": "qwen2.5-coder-7b", "object": "model"},
        ]
    }

    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=mock_models_response)
    )
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="hermes-3-llama-3.1-8b",
        http_client=mock_http_client,
    )

    models = client.probe_models()
    assert models == ["hermes-3-llama-3.1-8b", "qwen2.5-coder-7b"]
    assert client.check_availability() is True
    client.close()


# ===========================================================================
# 4. Acceptance Criterion 3: Timeout Handling
# ===========================================================================


def test_timeout_connect_raises_jev_ai_timeout() -> None:
    """Connection timeout must be caught and re-raised as JevAITimeout with explicit details."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out after 5.0s", request=request)

    mock_transport = httpx.MockTransport(handler)
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        timeout_seconds=5.0,
        http_client=mock_http_client,
    )

    with pytest.raises(JevAITimeout) as exc_info:
        client.chat([{"role": "user", "content": "hi"}])

    assert issubclass(JevAITimeout, JevAIUnavailable)
    assert exc_info.value.timeout_type in ("connect", "request")
    assert "timeout" in str(exc_info.value).lower()
    client.close()


def test_timeout_read_raises_jev_ai_timeout() -> None:
    """Read timeout while waiting for inference must be re-raised as JevAITimeout."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out after 60.0s", request=request)

    mock_transport = httpx.MockTransport(handler)
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        timeout_seconds=60.0,
        http_client=mock_http_client,
    )

    with pytest.raises(JevAITimeout) as exc_info:
        client.chat([{"role": "user", "content": "generate detailed report"}])

    assert exc_info.value.timeout_type in ("read", "request")
    assert "timeout" in str(exc_info.value).lower()
    client.close()


# ===========================================================================
# 5. Acceptance Criterion 4: Network Failure Handling
# ===========================================================================


def test_network_connection_refused_raises_connection_error() -> None:
    """Connection refused (e.g. LM Studio not listening) raises JevAIConnectionError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("[WinError 10061] No connection could be made", request=request)

    mock_transport = httpx.MockTransport(handler)
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        http_client=mock_http_client,
    )

    with pytest.raises(JevAIConnectionError) as exc_info:
        client.chat([{"role": "user", "content": "ping"}])

    assert issubclass(JevAIConnectionError, JevAIUnavailable)
    assert "failed to connect" in str(exc_info.value).lower() or "connection" in str(exc_info.value).lower()
    client.close()


def test_network_transport_disconnect_raises_connection_error() -> None:
    """Remote protocol / transport disconnection raises JevAIConnectionError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.RemoteProtocolError("Server disconnected unexpectedly", request=request)

    mock_transport = httpx.MockTransport(handler)
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        http_client=mock_http_client,
    )

    with pytest.raises(JevAIConnectionError):
        client.chat([{"role": "user", "content": "ping"}])

    client.close()


def test_http_500_server_error_raises_jev_ai_http_error() -> None:
    """HTTP 500 from LM Studio raises JevAIHTTPError with status_code."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(500, text="Internal Server Error: Out of memory")
    )
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        http_client=mock_http_client,
    )

    with pytest.raises(JevAIHTTPError) as exc_info:
        client.chat([{"role": "user", "content": "ping"}])

    assert issubclass(JevAIHTTPError, JevAIUnavailable)
    assert exc_info.value.status_code == 500
    assert "500" in str(exc_info.value)
    client.close()


def test_http_404_not_found_raises_jev_ai_http_error() -> None:
    """HTTP 404 (endpoint or model not found) raises JevAIHTTPError."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(404, text="Model not found")
    )
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="nonexistent-model",
        http_client=mock_http_client,
    )

    with pytest.raises(JevAIHTTPError) as exc_info:
        client.chat([{"role": "user", "content": "ping"}])

    assert exc_info.value.status_code == 404
    client.close()


# ===========================================================================
# 6. Response Validation & Edge Cases
# ===========================================================================


def test_response_malformed_json_raises_response_error() -> None:
    """When LM Studio returns non-JSON garbage, raise JevAIResponseError."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, text="<!DOCTYPE html><html><body>Error</body></html>")
    )
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        http_client=mock_http_client,
    )

    with pytest.raises(JevAIResponseError):
        client.chat([{"role": "user", "content": "test"}])

    assert issubclass(JevAIResponseError, JevAIUnavailable)
    client.close()


def test_response_missing_choices_raises_response_error() -> None:
    """When response is a JSON dict but missing 'choices', raise JevAIResponseError."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"id": "chatcmpl-1", "created": 12345})
    )
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        http_client=mock_http_client,
    )

    with pytest.raises(JevAIResponseError):
        client.chat([{"role": "user", "content": "test"}])

    client.close()


def test_response_empty_choices_array_raises_response_error() -> None:
    """When 'choices' is an empty list [], raise JevAIResponseError."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"choices": []})
    )
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        http_client=mock_http_client,
    )

    with pytest.raises(JevAIResponseError):
        client.chat([{"role": "user", "content": "test"}])

    client.close()


def test_response_missing_message_or_content_raises_response_error() -> None:
    """When choice element is missing 'message' or 'content', raise JevAIResponseError."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"choices": [{"index": 0, "message": {}}]})
    )
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        http_client=mock_http_client,
    )

    with pytest.raises(JevAIResponseError):
        client.chat([{"role": "user", "content": "test"}])

    client.close()


# ===========================================================================
# 7. Lifecycle & Resource Management
# ===========================================================================


def test_client_context_manager() -> None:
    """Verify that JevAIClient can be used as a context manager and cleanly closes."""
    with JevAIClient(base_url="http://localhost:1234/v1", model_id="test-model") as client:
        assert client.enabled is True
    # Successfully exited without exception


def test_client_reused_across_multiple_requests() -> None:
    """Verify that a single client instance can execute multiple requests."""
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": f"Response {count}"},
                    }
                ]
            },
        )

    mock_transport = httpx.MockTransport(handler)
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        http_client=mock_http_client,
    )

    r1 = client.chat([{"role": "user", "content": "one"}])
    r2 = client.chat([{"role": "user", "content": "two"}])
    r3 = client.chat([{"role": "user", "content": "three"}])

    assert r1.text == "Response 1"
    assert r2.text == "Response 2"
    assert r3.text == "Response 3"
    assert count == 3
    client.close()


# ===========================================================================
# 8. Scientific Boundary & Detector Independence
# ===========================================================================


def test_detector_pipeline_zero_jev_ai_dependency() -> None:
    """Verify that Detector Pipeline can execute completely without JevAIClient."""
    from x_sentinel.detection.pipeline import DetectorPipeline

    # Initializing and inspecting pipeline imports must not require Jev AI
    assert hasattr(DetectorPipeline, "evaluate")
    assert hasattr(DetectorPipeline, "scores")
    # JevAIClient is not in pipeline attributes
    assert not hasattr(DetectorPipeline, "jev_ai_client")


# ===========================================================================
# 9. Extended Security, Package Exports & Orchestrator Integration
# ===========================================================================


def test_package_exports_from_jev_ai_root() -> None:
    """Verify clean top-level exports from x_sentinel.jev_ai package."""
    import x_sentinel.jev_ai as jev_ai_pkg

    expected_exports = [
        "JevAIClient",
        "JevAIConfigurationError",
        "JevAIConnectionError",
        "JevAIDisabledError",
        "JevAIError",
        "JevAIHTTPError",
        "JevAIResponseError",
        "JevAITimeout",
        "JevAIUnavailable",
        "JevContext",
        "JevMode",
        "JevRequest",
        "JevResponse",
        "JevStatus",
        "JevStatusResponse",
    ]
    for exp in expected_exports:
        assert hasattr(jev_ai_pkg, exp), f"Package missing export: {exp}"


def test_api_key_header_forwarding_when_configured() -> None:
    """When api_key is configured, it must be forwarded in the Authorization header."""
    captured_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(dict(request.headers))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    mock_transport = httpx.MockTransport(handler)
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        api_key="secret-bearer-token-123",
        http_client=mock_http_client,
    )

    client.chat([{"role": "user", "content": "hello"}])
    assert "authorization" in captured_headers
    assert captured_headers["authorization"] == "Bearer secret-bearer-token-123"
    client.close()


def test_store_raw_preserves_full_runtime_payload() -> None:
    """When store_raw=True, full raw dictionary from LM Studio is preserved in JevResponse.raw."""
    raw_payload = {
        "id": "chatcmpl-raw-test",
        "choices": [{"message": {"content": "detailed analysis"}}],
        "usage": {"total_tokens": 100},
    }

    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=raw_payload)
    )
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="test-model",
        store_raw=True,
        http_client=mock_http_client,
    )

    res = client.chat([{"role": "user", "content": "test"}])
    assert res.raw == raw_payload
    client.close()


def test_orchestrator_integration_with_jev_ai_client() -> None:
    """Verify that JevAIOrchestrator seamlessly integrates with JevAIClient."""
    from x_sentinel.jev_ai.orchestrator import JevAIOrchestrator
    from x_sentinel.jev_ai.schemas import JevContext, JevMode, JevRequest

    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "Grounded explanation based on M1 score 0.42.",
                }
            }
        ]
    }

    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=mock_response)
    )
    mock_http_client = httpx.Client(transport=mock_transport)

    client = JevAIClient(
        base_url="http://localhost:1234/v1",
        model_id="hermes-3-test",
        http_client=mock_http_client,
    )

    orchestrator = JevAIOrchestrator(client=client)
    req = JevRequest(
        mode=JevMode.EXPLAIN,
        context=JevContext(decision="alert", detector_scores={"M1": 0.42}),
    )

    response, digest = orchestrator.run(req)
    assert isinstance(response, JevResponse)
    assert response.text == "Grounded explanation based on M1 score 0.42."
    assert len(digest) == 64
    client.close()
