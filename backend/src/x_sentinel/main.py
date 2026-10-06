from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from x_sentinel.api.routes import router
from x_sentinel.config import settings
from x_sentinel.database.health import database_health

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
def ready() -> dict[str, object]:
    db = database_health() if settings.database_required else None
    db_ready = True if db is None else db.ok
    scientific_ready = False
    config_ready = settings.demo_mode
    is_ready = db_ready and config_ready
    blockers: list[str] = []
    if db is not None and not db.ok:
        blockers.append("database unavailable or migration revision mismatch")
    if not settings.demo_mode:
        blockers.append("freeze view-map/model/M4/fusion configuration")
    payload = {
        "status": "ready" if is_ready else "blocked",
        "demo_mode": settings.demo_mode,
        "scientific_ready": scientific_ready,
        "database": None if db is None else db.to_dict(),
        "jev_ai": {
            "enabled": settings.jev_ai_enabled,
            "advisory_only": settings.jev_ai_advisory_only,
            "model_id": settings.jev_ai_model if settings.jev_ai_enabled else None,
            "readiness_blocking": False,
        },
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
        "database_revision": None if db is None else db.current_revision,
        "expected_database_revision": settings.expected_db_revision,
        "scientific_config_status": "TBD_MUST_FREEZE" if settings.demo_mode else "CHECK_CONFIGS",
        "jev_ai": {
            "enabled": settings.jev_ai_enabled,
            "model_id": settings.jev_ai_model if settings.jev_ai_enabled else None,
            "advisory_only": settings.jev_ai_advisory_only,
            "local_only": settings.jev_ai_local_only,
        },
    }
