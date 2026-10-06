from __future__ import annotations

import httpx

from x_sentinel.config import settings
from x_sentinel.jev_ai.guardrails import validate_local_endpoint
from x_sentinel.jev_ai.schemas import JevStatus, JevStatusResponse


def get_jev_status(client: httpx.Client | None = None) -> JevStatusResponse:
    """Evaluate and report independent Jev AI integration status.
    
    Hard boundaries:
    1. If Jev AI is disabled, zero network calls are performed.
    2. Jev AI availability is strictly non-blocking for detector/backend readiness.
    3. Endpoint labels are non-secret; internal network URLs and credentials are never exposed.
    """
    if not settings.jev_ai_enabled:
        return JevStatusResponse(
            enabled=False,
            status=JevStatus.DISABLED,
            advisory_only=settings.jev_ai_advisory_only,
            model_id=None,
            prompt_version=settings.jev_ai_prompt_version,
            endpoint_label="lm_studio_local",
            readiness_blocking=False,
            error=None,
        )

    # Validate local endpoint allowlist
    if settings.jev_ai_local_only:
        try:
            validate_local_endpoint(settings.jev_ai_base_url)
        except Exception as exc:
            return JevStatusResponse(
                enabled=True,
                status=JevStatus.MISCONFIGURED,
                advisory_only=settings.jev_ai_advisory_only,
                model_id=settings.jev_ai_model,
                prompt_version=settings.jev_ai_prompt_version,
                endpoint_label="lm_studio_local",
                readiness_blocking=False,
                error=f"XS_AI_CONTEXT_BLOCKED: {exc}",
            )

    # Probe LM Studio models endpoint with bounded timeout
    probe_url = f"{settings.jev_ai_base_url.rstrip('/')}/models"
    probe_timeout = min(settings.jev_ai_timeout_seconds, 2.0)

    try:
        if client is not None:
            resp = client.get(probe_url)
        else:
            with httpx.Client(timeout=probe_timeout) as http_client:
                resp = http_client.get(probe_url)

        if resp.status_code == 200:
            data = resp.json()
            models_list: list[str] = []
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                models_list = [
                    str(m["id"])
                    for m in data["data"]
                    if isinstance(m, dict) and "id" in m
                ]

            is_degraded = bool(
                models_list
                and settings.jev_ai_model not in models_list
                and settings.jev_ai_model != "jev-local-TBD"
            )

            return JevStatusResponse(
                enabled=True,
                status=JevStatus.DEGRADED if is_degraded else JevStatus.AVAILABLE,
                advisory_only=settings.jev_ai_advisory_only,
                model_id=settings.jev_ai_model,
                prompt_version=settings.jev_ai_prompt_version,
                endpoint_label="lm_studio_local",
                readiness_blocking=False,
                error=(
                    f"configured model '{settings.jev_ai_model}' "
                    "not found in LM Studio loaded models"
                    if is_degraded
                    else None
                ),
            )
        else:
            return JevStatusResponse(
                enabled=True,
                status=JevStatus.UNAVAILABLE,
                advisory_only=settings.jev_ai_advisory_only,
                model_id=settings.jev_ai_model,
                prompt_version=settings.jev_ai_prompt_version,
                endpoint_label="lm_studio_local",
                readiness_blocking=False,
                error=f"XS_AI_UNAVAILABLE: LM Studio probe returned status {resp.status_code}",
            )
    except Exception:
        return JevStatusResponse(
            enabled=True,
            status=JevStatus.UNAVAILABLE,
            advisory_only=settings.jev_ai_advisory_only,
            model_id=settings.jev_ai_model,
            prompt_version=settings.jev_ai_prompt_version,
            endpoint_label="lm_studio_local",
            readiness_blocking=False,
            error="XS_AI_UNAVAILABLE: local LM Studio unreachable",
        )
