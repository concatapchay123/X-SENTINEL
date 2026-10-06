from __future__ import annotations

from fastapi import APIRouter, HTTPException

from x_sentinel.api.schemas import AnalysisResponse, VectorAnalysisRequest
from x_sentinel.config import settings
from x_sentinel.data.schema import VectorValidationError
from x_sentinel.jev_ai.schemas import JevStatusResponse
from x_sentinel.jev_ai.status import get_jev_status
from x_sentinel.services.analysis_service import AnalysisService

router = APIRouter()


@router.get("/v1/ai/status", response_model=JevStatusResponse)
def ai_status() -> JevStatusResponse:
    return get_jev_status()


def _service() -> AnalysisService:
    view_name = "views.demo.yaml" if settings.demo_mode else "views.scientific.yaml"
    return AnalysisService(
        audit_path=settings.audit_log_path,
        view_map_path=settings.config_dir / view_name,
        demo_mode=settings.demo_mode,
    )


@router.post("/v1/analyze/vector", response_model=AnalysisResponse)
def analyze_vector(req: VectorAnalysisRequest) -> AnalysisResponse:
    try:
        result = _service().analyze_vector(req.features, req.request_id)
        return AnalysisResponse(**result.__dict__)
    except VectorValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "XS_INPUT_INVALID", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "XS_CONFIG_UNRESOLVED", "message": str(exc)}) from exc


@router.post("/v1/analyze/file")
def analyze_file() -> None:
    raise HTTPException(status_code=501, detail={"code": "XS_FEATURE_DISABLED", "message": "raw PE/LIEF is Phase 2"})
