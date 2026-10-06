from __future__ import annotations

import time
from typing import Any

import httpx

from x_sentinel.jev_ai.guardrails import validate_local_endpoint
from x_sentinel.jev_ai.schemas import JevResponse


class JevAIUnavailable(RuntimeError):
    pass


class JevAIClient:
    def __init__(
        self,
        *,
        base_url: str,
        model_id: str,
        timeout_seconds: float = 60.0,
        temperature: float = 0.1,
        prompt_version: str = "jev-v3.0.0",
        local_only: bool = True,
    ) -> None:
        if local_only:
            validate_local_endpoint(base_url)
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.prompt_version = prompt_version

    def chat(self, messages: list[dict[str, str]]) -> JevResponse:
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model_id,
                        "messages": messages,
                        "temperature": self.temperature,
                    },
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise JevAIUnavailable(str(exc)) from exc

        try:
            text = str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise JevAIUnavailable("LM Studio response did not match chat-completions contract") from exc

        return JevResponse(
            text=text,
            model_id=self.model_id,
            prompt_version=self.prompt_version,
            advisory_only=True,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            raw=None,
        )
