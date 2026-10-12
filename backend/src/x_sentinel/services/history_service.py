from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from x_sentinel.api.schemas import (
    AlertSummary,
    AnalysisDetailResponse,
    AnalysisJobSummary,
    AnalysisResultDetail,
    DetectorScoreItem,
)
from x_sentinel.database.models import (
    AnalysisResultRecord,
    Artifact,
)
from x_sentinel.database.repositories.analysis import (
    AnalysisJobRepository,
    AnalysisResultRepository,
)


class HistoryService:
    """Service layer orchestrating analysis history queries and detail retrieval."""

    def __init__(
        self,
        job_repo: AnalysisJobRepository | None = None,
        result_repo: AnalysisResultRepository | None = None,
    ):
        self._job_repo = job_repo
        self._result_repo = result_repo

    def _get_job_repo(self, session: Session) -> AnalysisJobRepository:
        return self._job_repo or AnalysisJobRepository(session)

    def _get_result_repo(self, session: Session) -> AnalysisResultRepository:
        return self._result_repo or AnalysisResultRepository(session)

    def list_history(
        self,
        session: Session,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        decision: str | None = None,
        input_mode: str | None = None,
        demo_mode: bool | None = None,
    ) -> tuple[list[AnalysisJobSummary], int]:
        """Lists historical analysis jobs with filters, pagination, and result summaries."""
        repo = self._get_job_repo(session)
        jobs, total = repo.list_jobs_filtered(
            limit=limit,
            offset=offset,
            status=status,
            decision=decision,
            input_mode=input_mode,
            demo_mode=demo_mode,
        )

        job_ids = [j.id for j in jobs]
        results_by_job: dict[uuid.UUID, AnalysisResultRecord] = {}
        if job_ids:
            records = session.scalars(
                select(AnalysisResultRecord).where(AnalysisResultRecord.analysis_job_id.in_(job_ids))
            ).all()
            results_by_job = {r.analysis_job_id: r for r in records}

        items: list[AnalysisJobSummary] = []
        for j in jobs:
            res = results_by_job.get(j.id)
            items.append(
                AnalysisJobSummary(
                    id=str(j.id),
                    request_id=j.request_id,
                    status=j.status,
                    input_mode=j.input_mode,
                    demo_mode=j.demo_mode,
                    decision=res.decision if res else None,
                    malware_score=res.malware_score if res else None,
                    suspicion_score=res.suspicion_score if res else None,
                    created_at=j.created_at.isoformat() if j.created_at else "",
                    completed_at=j.completed_at.isoformat() if j.completed_at else None,
                )
            )

        return items, total

    def get_analysis_detail(
        self,
        session: Session,
        identifier: str,
    ) -> AnalysisDetailResponse | None:
        """Retrieves full analysis record including detector scores, alerts, and artifacts."""
        repo = self._get_job_repo(session)
        job, result_record, scores, alerts = repo.get_detail(identifier)
        if job is None:
            return None

        # Look up evidence artifact if available
        evidence_artifact = session.scalar(
            select(Artifact).where(Artifact.analysis_job_id == job.id, Artifact.kind == "evidence")
        )
        evidence_ref = evidence_artifact.sha256 if evidence_artifact else None

        detail_result: AnalysisResultDetail | None = None
        if result_record is not None:
            detail_result = AnalysisResultDetail(
                malware_score=result_record.malware_score,
                suspicion_score=result_record.suspicion_score,
                threshold=result_record.threshold,
                decision=result_record.decision,
                latency_ms=result_record.latency_ms,
                view_contributions=result_record.view_contributions or {},
                evidence_uri=result_record.evidence_uri,
                result_json=result_record.result_json or {},
            )

        score_items = [
            DetectorScoreItem(
                detector_code=s.detector_code,
                score=s.score,
                diagnostics=s.diagnostics or {},
            )
            for s in scores
        ]

        alert_items = [
            AlertSummary(
                id=str(a.id),
                analysis_job_id=str(a.analysis_job_id),
                severity=a.severity,
                status=a.status,
                reason=a.reason,
                created_at=a.created_at.isoformat() if a.created_at else "",
                resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            )
            for a in alerts
        ]

        return AnalysisDetailResponse(
            id=str(job.id),
            request_id=job.request_id,
            status=job.status,
            input_mode=job.input_mode,
            input_sha256=job.input_sha256,
            demo_mode=job.demo_mode,
            created_at=job.created_at.isoformat() if job.created_at else "",
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            error_code=job.error_code,
            error_message=job.error_message,
            result=detail_result,
            scores=score_items,
            alerts=alert_items,
            evidence_ref=evidence_ref,
        )
