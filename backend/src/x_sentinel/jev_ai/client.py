from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from x_sentinel.jev_ai.guardrails import (
    ALLOWED_LOCAL_HOSTS,
    validate_local_endpoint,
)
from x_sentinel.jev_ai.schemas import JevResponse

logger = logging.getLogger("x_sentinel.jev_ai.client")


class JevAIError(RuntimeError):
    """Base exception for all Jev AI runtime client errors."""

    pass


class JevAIUnavailable(JevAIError):
    """Raised when Jev AI LM Studio runtime is unavailable, disabled, or failed.
    Maintains backward compatibility with callers catching JevAIUnavailable."""

    pass


class JevAIDisabledError(JevAIUnavailable):
    """Raised when Jev AI is disabled and an inference or network request is attempted."""

    pass


class JevAIConfigurationError(JevAIError):
    """Raised when runtime client configuration is invalid."""

    pass


class JevAITimeout(JevAIUnavailable):
    """Raised when request to LM Studio exceeds connect, read, or overall timeout."""

    def __init__(
        self,
        message: str,
        *,
        timeout_type: str = "request",
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.timeout_type = timeout_type
        self.timeout_seconds = timeout_seconds


class JevAIConnectionError(JevAIUnavailable):
    """Raised when network connection to LM Studio fails (refused, unreachable, disconnect)."""

    pass


class JevAIHTTPError(JevAIUnavailable):
    """Raised when LM Studio returns an HTTP 4xx or 5xx status code."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class JevAIResponseError(JevAIUnavailable):
    """Raised when LM Studio returns an invalid or malformed response structure."""

    pass


class JevAIClient:
    """Local OpenAI-compatible HTTP client for LM Studio runtime inference.

    Adheres to strict X-SENTINEL architectural constraints:
    1. Pure headless REST communication;
    2. Disabled mode guarantees exactly zero outbound network calls;
    3. Advisory-only outputs (does not alter detector decisions);
    4. Guardrails enforce loopback / private-host network boundaries;
    5. Clean resource lifecycle management with connection pooling and timeouts.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model_id: str,
        enabled: bool = True,
        timeout_seconds: float = 60.0,
        connect_timeout: float | None = None,
        read_timeout: float | None = None,
        write_timeout: float | None = None,
        pool_timeout: float | None = None,
        temperature: float = 0.1,
        max_output_tokens: int | None = 1200,
        prompt_version: str = "jev-v3.0.0",
        local_only: bool = True,
        allowed_hosts: set[str] | list[str] | None = None,
        api_key: str | None = None,
        store_raw: bool = False,
        http_client: httpx.Client | None = None,
    ) -> None:
        # Validate model_id
        if not model_id or not model_id.strip():
            raise JevAIConfigurationError("model_id must not be empty or whitespace")

        # Validate base_url
        if not base_url or not base_url.strip():
            raise JevAIConfigurationError("base_url must not be empty or whitespace")

        parsed = urlparse(base_url.strip())
        if parsed.scheme not in {"http", "https"}:
            raise JevAIConfigurationError(
                f"base_url scheme must be 'http' or 'https'; got '{parsed.scheme}'"
            )
        if not parsed.hostname:
            raise JevAIConfigurationError(f"base_url missing valid host: '{base_url}'")

        # Local allowlist enforcement
        if local_only:
            allowed_hosts_set = (
                set(allowed_hosts) if allowed_hosts is not None else ALLOWED_LOCAL_HOSTS
            )
            validate_local_endpoint(base_url, allowed_hosts=allowed_hosts_set)

        # Validate timeout
        if timeout_seconds <= 0:
            raise JevAIConfigurationError(f"timeout_seconds must be > 0; got {timeout_seconds}")

        # Validate temperature
        if not (0.0 <= temperature <= 2.0):
            raise JevAIConfigurationError(
                f"temperature must be between 0.0 and 2.0; got {temperature}"
            )

        # Validate max_output_tokens if given
        if max_output_tokens is not None and max_output_tokens <= 0:
            raise JevAIConfigurationError(f"max_output_tokens must be > 0; got {max_output_tokens}")

        self.base_url = base_url.rstrip("/")
        self.model_id = model_id.strip()
        self.enabled = enabled
        self.timeout_seconds = float(timeout_seconds)
        self.connect_timeout = float(connect_timeout) if connect_timeout is not None else None
        self.read_timeout = float(read_timeout) if read_timeout is not None else None
        self.write_timeout = float(write_timeout) if write_timeout is not None else None
        self.pool_timeout = float(pool_timeout) if pool_timeout is not None else None
        self.temperature = float(temperature)
        self.max_output_tokens = max_output_tokens
        self.prompt_version = prompt_version
        self.local_only = local_only
        self.allowed_hosts = allowed_hosts
        self.api_key = api_key
        self.store_raw = store_raw

        # Lifecycle & connection pooling
        if http_client is not None:
            self._client: httpx.Client | None = http_client
            self._owns_client = False
        else:
            self._client = None
            self._owns_client = True

    @property
    def is_enabled(self) -> bool:
        """Return True if Jev AI runtime is enabled."""
        return self.enabled

    @property
    def endpoint(self) -> str:
        """Canonical OpenAI-compatible chat completions endpoint."""
        return f"{self.base_url}/chat/completions"

    def _build_timeout(self) -> httpx.Timeout:
        """Construct granular httpx.Timeout from configuration."""
        return httpx.Timeout(
            timeout=self.timeout_seconds,
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=self.write_timeout,
            pool=self.pool_timeout,
        )

    def _get_client(self) -> httpx.Client:
        """Retrieve existing HTTP client or lazily instantiate internal managed client."""
        if self._client is None or (self._owns_client and self._client.is_closed):
            self._client = httpx.Client(timeout=self._build_timeout())
            self._owns_client = True
        return self._client

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        logprobs: bool = False,
        top_logprobs: int | None = None,
    ) -> JevResponse:
        """Execute OpenAI-compatible chat completion request against LM Studio runtime.

        Args:
            messages: List of message objects with 'role' and 'content' keys.
            temperature: Optional per-request temperature override.
            max_output_tokens: Optional per-request token ceiling override.
            logprobs: Whether to request token log probabilities.
            top_logprobs: Number of most likely tokens to return logprobs for.

        Returns:
            JevResponse: Validated advisory analysis result with latency and metadata.

        Raises:
            JevAIDisabledError: When runtime client is disabled (zero network calls).
            JevAITimeout: On connection, read, or request timeout.
            JevAIConnectionError: On connection refused, network unreachable, disconnect.
            JevAIHTTPError: When LM Studio returns HTTP 4xx or 5xx.
            JevAIResponseError: When response JSON is malformed or missing required keys.
        """
        # Hard invariant: Disabled mode MUST perform exactly ZERO network calls.
        if not self.enabled:
            raise JevAIDisabledError("Jev AI runtime client is disabled (XS_JEV_AI_ENABLED=false)")

        started = time.perf_counter()

        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "stream": False,
        }
        tokens = self.max_output_tokens if max_output_tokens is None else max_output_tokens
        if tokens is not None:
            payload["max_tokens"] = tokens
        if logprobs:
            payload["logprobs"] = True
            if top_logprobs is not None:
                payload["top_logprobs"] = top_logprobs

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "X-SENTINEL-V3-JevAI/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            client = self._get_client()
            response = client.post(
                self.endpoint,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.ConnectTimeout as exc:
            eff_timeout = self.connect_timeout or self.timeout_seconds
            logger.warning("LM Studio connect timeout after %ss at %s", eff_timeout, self.base_url)
            raise JevAITimeout(
                f"Connection timeout to LM Studio at {self.base_url} after {eff_timeout}s",
                timeout_type="connect",
                timeout_seconds=eff_timeout,
            ) from exc
        except httpx.ReadTimeout as exc:
            eff_timeout = self.read_timeout or self.timeout_seconds
            logger.warning("LM Studio read timeout after %ss at %s", eff_timeout, self.base_url)
            raise JevAITimeout(
                f"Read timeout waiting for LM Studio response after {eff_timeout}s",
                timeout_type="read",
                timeout_seconds=eff_timeout,
            ) from exc
        except httpx.TimeoutException as exc:
            logger.warning("LM Studio request timeout after %ss: %s", self.timeout_seconds, exc)
            raise JevAITimeout(
                f"Request to LM Studio timed out after {self.timeout_seconds}s: {exc}",
                timeout_type="request",
                timeout_seconds=self.timeout_seconds,
            ) from exc
        except httpx.ConnectError as exc:
            logger.warning("LM Studio connection refused at %s: %s", self.base_url, exc)
            raise JevAIConnectionError(
                f"Failed to connect to LM Studio at {self.base_url} "
                "(connection refused or runtime not listening)"
            ) from exc
        except (httpx.NetworkError, httpx.RemoteProtocolError, httpx.TransportError) as exc:
            logger.warning("LM Studio transport failure at %s: %s", self.base_url, exc)
            raise JevAIConnectionError(
                f"Network transport error communicating with LM Studio: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            resp_text = exc.response.text[:200] if exc.response is not None else ""
            logger.warning("LM Studio returned HTTP %s: %s", status_code, resp_text)
            raise JevAIHTTPError(
                f"LM Studio returned HTTP {status_code}: {resp_text}",
                status_code=status_code,
                response_body=resp_text,
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("LM Studio HTTP error: %s", exc)
            raise JevAIUnavailable(f"HTTP error communicating with LM Studio: {exc}") from exc

        # Response parsing & validation
        try:
            data: Any = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error("LM Studio returned non-JSON payload")
            raise JevAIResponseError("LM Studio returned malformed non-JSON response") from exc

        if not isinstance(data, dict):
            raise JevAIResponseError(
                f"LM Studio response root must be a JSON object; got {type(data).__name__}"
            )

        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            raise JevAIResponseError("LM Studio response missing non-empty 'choices' array")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise JevAIResponseError("LM Studio choices[0] is not a dictionary")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise JevAIResponseError("LM Studio choices[0] missing 'message' dictionary")

        content = message.get("content")
        if content is None:
            raise JevAIResponseError("LM Studio choices[0].message missing 'content' field")

        text = str(content)
        returned_model = str(data.get("model")) if data.get("model") else self.model_id
        latency_ms = (time.perf_counter() - started) * 1000.0

        logprobs_data = first_choice.get("logprobs")
        if not isinstance(logprobs_data, dict):
            logprobs_data = None

        return JevResponse(
            text=text,
            model_id=returned_model,
            prompt_version=self.prompt_version,
            advisory_only=True,
            latency_ms=latency_ms,
            raw=data if self.store_raw else None,
            logprobs=logprobs_data,
        )

    def probe_models(self) -> list[str]:
        """Probe LM Studio /models endpoint to discover loaded models.

        Returns:
            list[str]: Model identifiers reported by LM Studio.
            Returns empty list if disabled or if probe fails.
            Guarantees exactly zero network calls when disabled.
        """
        if not self.enabled:
            return []

        try:
            client = self._get_client()
            resp = client.get(
                f"{self.base_url}/models",
                timeout=min(self.timeout_seconds, 2.0),
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                    return [str(m["id"]) for m in data["data"] if isinstance(m, dict) and "id" in m]
        except Exception as exc:
            logger.debug("LM Studio models probe failed: %s", exc)
            return []
        return []

    def check_availability(self) -> bool:
        """Check whether LM Studio is reachable and configured model is loaded.

        Guarantees zero network calls when disabled.
        """
        if not self.enabled:
            return False
        models = self.probe_models()
        if not models:
            return False
        if self.model_id == "jev-local-TBD":
            return True
        return self.model_id in models

    def close(self) -> None:
        """Release underlying HTTP client connections."""
        if self._owns_client and self._client is not None:
            try:
                self._client.close()
            except Exception as exc:
                logger.debug("Error closing HTTP client: %s", exc)
            finally:
                self._client = None

    def __enter__(self) -> JevAIClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    @classmethod
    def from_settings(cls, settings_obj: Any = None, **overrides: Any) -> JevAIClient:
        """Factory method constructing JevAIClient from application Settings."""
        if settings_obj is None:
            from x_sentinel.config import settings as app_settings

            settings_obj = app_settings

        yaml_config: dict[str, Any] = {}
        if hasattr(settings_obj, "get_jev_ai_config"):
            try:
                yaml_config = settings_obj.get_jev_ai_config() or {}
            except Exception as exc:
                logger.warning("Could not load jev_ai.yaml in from_settings: %s", exc)

        req_cfg = yaml_config.get("request", {})
        sec_cfg = yaml_config.get("security", {})

        allowed_hosts = sec_cfg.get("allowed_hosts")
        max_output_tokens = req_cfg.get("max_output_tokens", 1200)

        kwargs: dict[str, Any] = {
            "base_url": getattr(settings_obj, "jev_ai_base_url", "http://localhost:1234/v1"),
            "model_id": getattr(settings_obj, "jev_ai_model", "jev-local-TBD"),
            "enabled": getattr(settings_obj, "jev_ai_enabled", False),
            "timeout_seconds": getattr(settings_obj, "jev_ai_timeout_seconds", 60.0),
            "temperature": getattr(settings_obj, "jev_ai_temperature", 0.1),
            "prompt_version": getattr(settings_obj, "jev_ai_prompt_version", "jev-v3.0.0"),
            "local_only": getattr(settings_obj, "jev_ai_local_only", True),
            "allowed_hosts": allowed_hosts,
            "max_output_tokens": max_output_tokens,
            "store_raw": getattr(settings_obj, "jev_ai_store_response_text", True),
        }
        kwargs.update(overrides)
        return cls(**kwargs)

    @classmethod
    def from_config(cls, config_dict: dict[str, Any], **overrides: Any) -> JevAIClient:
        """Factory method constructing JevAIClient from dictionary configuration."""
        req_cfg = config_dict.get("request", {})
        sec_cfg = config_dict.get("security", {})

        kwargs: dict[str, Any] = {
            "base_url": config_dict.get("base_url", "http://localhost:1234/v1"),
            "model_id": config_dict.get("model_id", "jev-local-TBD"),
            "enabled": config_dict.get("enabled", True),
            "timeout_seconds": req_cfg.get("timeout_seconds", 60.0),
            "temperature": req_cfg.get("temperature", 0.1),
            "max_output_tokens": req_cfg.get("max_output_tokens", 1200),
            "prompt_version": config_dict.get("prompt_version", "jev-v3.0.0"),
            "local_only": sec_cfg.get("local_only", True),
            "allowed_hosts": sec_cfg.get("allowed_hosts"),
        }
        kwargs.update(overrides)
        return cls(**kwargs)
