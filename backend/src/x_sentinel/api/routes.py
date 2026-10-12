from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from x_sentinel.api.schemas import (
    AlertListResponse,
    AlertStatusUpdateRequest,
    AlertSummary,
    AnalysisDetailResponse,
    AnalysisHistoryListResponse,
    AnalysisResponse,
    CanonicalEvidenceResponse,
    VectorAnalysisRequest,
)
from x_sentinel.audit.evidence import EvidenceIntegrityError
from x_sentinel.audit.writer import AuditWriteFailureError
from x_sentinel.config import settings
from x_sentinel.data.schema import VectorValidationError
from x_sentinel.database.session import get_db
from x_sentinel.jev_ai.schemas import JevStatusResponse
from x_sentinel.jev_ai.status import get_jev_status
from x_sentinel.security.auth import (
    ANONYMOUS_USER,
    AuthUser,
    Role,
    require_roles,
)
from x_sentinel.services.alert_service import AlertService
from x_sentinel.services.analysis_service import AnalysisService
from x_sentinel.services.evidence_service import EvidenceService
from x_sentinel.services.history_service import HistoryService

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependencies & Service Instantiation
# ---------------------------------------------------------------------------


def get_analysis_service(db: Session = Depends(get_db)) -> AnalysisService:
    view_name = "views.demo.yaml" if settings.demo_mode else "views.scientific.yaml"
    return AnalysisService(
        audit_path=settings.audit_log_path,
        view_map_path=settings.config_dir / view_name,
        demo_mode=settings.demo_mode,
        session=db,
    )


def get_history_service() -> HistoryService:
    return HistoryService()


def get_alert_service() -> AlertService:
    return AlertService()


def get_evidence_service() -> EvidenceService:
    return EvidenceService()


# ---------------------------------------------------------------------------
# Jev AI Status
# ---------------------------------------------------------------------------


@router.get(
    "/v1/ai/status",
    response_model=JevStatusResponse,
    tags=["AI Advisory"],
    summary="Get Jev AI LM Studio status",
)
def ai_status() -> JevStatusResponse:
    return get_jev_status()


# ---------------------------------------------------------------------------
# Core Analysis Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/v1/analyze/vector",
    response_model=AnalysisResponse,
    tags=["Analysis"],
    summary="Analyze a 2,381-feature EMBER vector",
)
def analyze_vector(
    req: VectorAnalysisRequest,
    service: AnalysisService = Depends(get_analysis_service),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(
        require_roles(Role.ADMIN.value, Role.ANALYST.value, Role.OPERATOR.value)
    ),
) -> AnalysisResponse:
    try:
        from x_sentinel.database.models import User
        persisted_user_id = None
        if user is not None and user.user_id != ANONYMOUS_USER.user_id:
            if db.get(User, user.user_id) is not None:
                persisted_user_id = user.user_id

        result = service.analyze_vector(
            features=req.features,
            request_id=req.request_id,
            session=db,
            user_id=persisted_user_id,
        )
        return AnalysisResponse(**result.__dict__)
    except VectorValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "XS_INPUT_INVALID", "message": str(exc)},
        ) from exc
    except AuditWriteFailureError as exc:
        msg = str(exc)
        if "Duplicate request_id" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "XS_DUPLICATE_REQUEST", "message": msg},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "XS_AUDIT_WRITE_FAILED", "message": msg},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "XS_CONFIG_UNRESOLVED", "message": str(exc)},
        ) from exc


@router.post(
    "/v1/analyze/file",
    tags=["Analysis"],
    summary="Analyze uploaded binary file (Phase 2 Gated)",
)
def analyze_file() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"code": "XS_FEATURE_DISABLED", "message": "raw PE/LIEF is Phase 2"},
    )


# ---------------------------------------------------------------------------
# Analysis History Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/v1/analysis",
    response_model=AnalysisHistoryListResponse,
    tags=["History"],
    summary="List analysis history with pagination and filtering",
)
def list_analysis_history(
    limit: int = Query(default=50, ge=1, le=1000, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    status_filter: str | None = Query(
        default=None, alias="status", description="Filter by job status"
    ),
    decision: str | None = Query(
        default=None, description="Filter by decision: pass, alert, quarantine"
    ),
    input_mode: str | None = Query(
        default=None, description="Filter by input mode: vector, raw_pe"
    ),
    demo_mode: bool | None = Query(default=None, description="Filter by demo_mode"),
    db: Session = Depends(get_db),
    history_svc: HistoryService = Depends(get_history_service),
    user: AuthUser = Depends(
        require_roles(
            Role.ADMIN.value, Role.ANALYST.value, Role.EVALUATOR.value, Role.OPERATOR.value
        )
    ),
) -> AnalysisHistoryListResponse:
    items, total = history_svc.list_history(
        session=db,
        limit=limit,
        offset=offset,
        status=status_filter,
        decision=decision,
        input_mode=input_mode,
        demo_mode=demo_mode,
    )
    return AnalysisHistoryListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/v1/analysis/{analysis_id}",
    response_model=AnalysisDetailResponse,
    tags=["History"],
    summary="Get detailed analysis result by UUID or request_id",
)
def get_analysis_detail(
    analysis_id: str,
    db: Session = Depends(get_db),
    history_svc: HistoryService = Depends(get_history_service),
    user: AuthUser = Depends(
        require_roles(
            Role.ADMIN.value, Role.ANALYST.value, Role.EVALUATOR.value, Role.OPERATOR.value
        )
    ),
) -> AnalysisDetailResponse:
    detail = history_svc.get_analysis_detail(session=db, identifier=analysis_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "XS_ANALYSIS_NOT_FOUND",
                "message": f"Analysis '{analysis_id}' not found.",
            },
        )
    return detail


# ---------------------------------------------------------------------------
# Canonical Evidence Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/v1/analysis/{analysis_id}/evidence",
    response_model=CanonicalEvidenceResponse,
    tags=["Evidence"],
    summary="Get verified canonical evidence for an analysis",
)
def get_analysis_evidence(
    analysis_id: str,
    db: Session = Depends(get_db),
    evidence_svc: EvidenceService = Depends(get_evidence_service),
    user: AuthUser = Depends(
        require_roles(Role.ADMIN.value, Role.ANALYST.value, Role.EVALUATOR.value)
    ),
) -> CanonicalEvidenceResponse:
    try:
        evidence = evidence_svc.get_canonical_evidence(session=db, identifier=analysis_id)
    except EvidenceIntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "XS_EVIDENCE_INTEGRITY_MISMATCH", "message": str(exc)},
        ) from exc

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "XS_EVIDENCE_NOT_FOUND",
                "message": f"Evidence for analysis '{analysis_id}' not found.",
            },
        )

    return evidence_svc.to_response(evidence)


# ---------------------------------------------------------------------------
# Alerts Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/v1/alerts",
    response_model=AlertListResponse,
    tags=["Alerts"],
    summary="List alerts with filtering and pagination",
)
def list_alerts(
    limit: int = Query(default=50, ge=1, le=1000, description="Query limit"),
    offset: int = Query(default=0, ge=0, description="Query offset"),
    severity: str | None = Query(
        default=None, description="Filter by severity: low, medium, high, critical"
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status: open, acknowledged, resolved, dismissed",
    ),
    analysis_job_id: str | None = Query(
        default=None, description="Filter by associated analysis job UUID"
    ),
    db: Session = Depends(get_db),
    alert_svc: AlertService = Depends(get_alert_service),
    user: AuthUser = Depends(
        require_roles(Role.ADMIN.value, Role.ANALYST.value, Role.OPERATOR.value)
    ),
) -> AlertListResponse:
    items, total = alert_svc.list_alerts(
        session=db,
        limit=limit,
        offset=offset,
        severity=severity,
        status=status_filter,
        analysis_job_id=analysis_job_id,
    )
    return AlertListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/v1/alerts/{alert_id}",
    response_model=AlertSummary,
    tags=["Alerts"],
    summary="Get alert details by UUID",
)
def get_alert_detail(
    alert_id: str,
    db: Session = Depends(get_db),
    alert_svc: AlertService = Depends(get_alert_service),
    user: AuthUser = Depends(
        require_roles(Role.ADMIN.value, Role.ANALYST.value, Role.OPERATOR.value)
    ),
) -> AlertSummary:
    alert = alert_svc.get_alert(session=db, alert_id=alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "XS_ALERT_NOT_FOUND", "message": f"Alert '{alert_id}' not found."},
        )
    return alert


@router.patch(
    "/v1/alerts/{alert_id}",
    response_model=AlertSummary,
    tags=["Alerts"],
    summary="Update alert lifecycle state",
)
def update_alert_status(
    alert_id: str,
    req: AlertStatusUpdateRequest,
    db: Session = Depends(get_db),
    alert_svc: AlertService = Depends(get_alert_service),
    user: AuthUser = Depends(require_roles(Role.ADMIN.value, Role.ANALYST.value)),
) -> AlertSummary:
    try:
        from x_sentinel.database.models import User
        persisted_actor_id = None
        if user is not None and user.user_id != ANONYMOUS_USER.user_id:
            if db.get(User, user.user_id) is not None:
                persisted_actor_id = user.user_id

        updated = alert_svc.update_alert_status(
            session=db,
            alert_id=alert_id,
            new_status=req.status,
            actor_id=persisted_actor_id,
        )
        return updated
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "XS_ALERT_NOT_FOUND", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "XS_INVALID_TRANSITION", "message": str(exc)},
        ) from exc
