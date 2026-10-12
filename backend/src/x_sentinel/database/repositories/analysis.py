from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from x_sentinel.database.models import AnalysisJob, AnalysisResultRecord


class AnalysisJobRepository:
    """Repository for AnalysisJob lifecycle operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, job_id: uuid.UUID) -> AnalysisJob | None:
        return self.session.get(AnalysisJob, job_id)

    def get_by_request_id(self, request_id: str) -> AnalysisJob | None:
        return self.session.scalar(
            select(AnalysisJob).where(AnalysisJob.request_id == request_id)
        )

    def add(self, job: AnalysisJob) -> AnalysisJob:
        self.session.add(job)
        self.session.flush()
        return job

    def list_jobs(self, limit: int = 100, offset: int = 0) -> Sequence[AnalysisJob]:
        stmt = (
            select(AnalysisJob)
            .order_by(desc(AnalysisJob.created_at))
            .limit(limit)
            .offset(offset)
        )
        return self.session.scalars(stmt).all()

    def update_status(
        self,
        job_id: uuid.UUID,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> AnalysisJob:
        job = self.session.get(AnalysisJob, job_id)
        if job is None:
            raise ValueError(f"AnalysisJob {job_id} not found.")
        job.status = status
        if error_code is not None:
            job.error_code = error_code
        if error_message is not None:
            job.error_message = error_message
        if status in {"completed", "failed", "quarantined"} and job.completed_at is None:
            job.completed_at = datetime.now(timezone.utc)
        self.session.flush()
        return job


class AnalysisResultRepository:
    """Repository for AnalysisResultRecord persistence."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_job_id(self, analysis_job_id: uuid.UUID) -> AnalysisResultRecord | None:
        return self.session.get(AnalysisResultRecord, analysis_job_id)

    def add(self, record: AnalysisResultRecord) -> AnalysisResultRecord:
        self.session.add(record)
        self.session.flush()
        return record
