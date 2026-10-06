from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from x_sentinel.api.routes import router
from x_sentinel.config import settings
from x_sentinel.database.health import database_health
from x_sentinel.jev_ai.status import get_jev_status

app = FastAPI(title="X-SENTINEL", version="0.3.0-baseline-v3")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "x-sentinel",
        "version": "v3",
        "demo_mode": settings.demo_mode,
        "jev_ai_enabled": settings.jev_ai_enabled,
    }


@app.get("/ready")
def ready() -> JSONResponse:
    db = database_health() if settings.database_required else None
    db_ready = True if db is None else db.ok
    scientific_ready = False
    config_ready = settings.demo_mode
    is_ready = db_ready and config_ready

    # Independent Jev AI status check (non-blocking for detector readiness)
    jev = get_jev_status()

    blockers: list[str] = []
    if db is not None and not db.ok:
        blockers.append(db.error or "database unavailable or migration revision mismatch")
    if not settings.demo_mode:
        blockers.append("freeze view-map/model/M4/fusion configuration")

    payload = {
        "status": "ready" if is_ready else "not_ready",
        "demo_mode": settings.demo_mode,
        "scientific_ready": scientific_ready,
        "database": None if db is None else db.to_dict(),
        "jev_ai": jev.model_dump(),
        "blockers": blockers,
    }
    return JSONResponse(status_code=200 if is_ready else 503, content=payload)


@app.get("/v1/config/status")
def config_status() -> dict[str, object]:
    db = database_health() if settings.database_required else None
    return {
        "environment": settings.env,
        "demo_mode": settings.demo_mode,
        "input_mode": settings.input_mode,
        "database_required": settings.database_required,
        "database_status": None if db is None else db.status,
        "database_revision": None if db is None else db.current_revision,
        "database_revision_status": None if db is None else db.revision_status,
        "expected_database_revision": settings.expected_db_revision,
        "scientific_config_status": "TBD_MUST_FREEZE" if settings.demo_mode else "CHECK_CONFIGS",
        "jev_ai": {
            "enabled": settings.jev_ai_enabled,
            "status": "disabled" if not settings.jev_ai_enabled else "configured",
            "model_id": settings.jev_ai_model if settings.jev_ai_enabled else None,
            "prompt_version": settings.jev_ai_prompt_version,
            "endpoint_label": "lm_studio_local",
            "advisory_only": settings.jev_ai_advisory_only,
            "local_only": settings.jev_ai_local_only,
        },
    }
