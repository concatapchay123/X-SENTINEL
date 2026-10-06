from __future__ import annotations

from x_sentinel.jev_ai.client import JevAIClient
from x_sentinel.jev_ai.prompt_builder import build_messages
from x_sentinel.jev_ai.schemas import JevRequest, JevResponse


class JevAIOrchestrator:
    """Advisory-only orchestration. Persistence/API wiring is implemented in PLAN-BE-13."""

    def __init__(self, client: JevAIClient, *, max_context_chars: int = 30_000) -> None:
        self.client = client
        self.max_context_chars = max_context_chars

    def run(self, request: JevRequest) -> tuple[JevResponse, str]:
        messages, input_digest = build_messages(request, max_chars=self.max_context_chars)
        response = self.client.chat(messages)
        return response, input_digest
