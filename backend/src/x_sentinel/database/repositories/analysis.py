from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from x_sentinel.database.models import (
    Alert,
    AnalysisJob,
    AnalysisResultRecord,
    DetectorScore,
)


class AnalysisJobRepository:
    """Repository for AnalysisJob lifecycle operations and history retrieval."""

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

    def list_jobs_filtered(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        decision: str | None = None,
        input_mode: str | None = None,
        demo_mode: bool | None = None,
    ) -> tuple[Sequence[AnalysisJob], int]:
        """Filters analysis jobs with pagination and optional decision join."""
        conditions = []
        if status is not None:
            conditions.append(AnalysisJob.status == status.lower().strip())
        if input_mode is not None:
            conditions.append(AnalysisJob.input_mode == input_mode.lower().strip())
        if demo_mode is not None:
            conditions.append(AnalysisJob.demo_mode == demo_mode)

        if decision is not None:
            # Join with AnalysisResultRecord to filter by decision
            dec_clean = decision.lower().strip()
            count_stmt = (
                select(func.count(AnalysisJob.id))
                .join(AnalysisResultRecord, AnalysisResultRecord.analysis_job_id == AnalysisJob.id)
                .where(AnalysisResultRecord.decision == dec_clean)
            )
            if conditions:
                count_stmt = count_stmt.where(*conditions)
            total = self.session.scalar(count_stmt) or 0

            stmt = (
                select(AnalysisJob)
                .join(AnalysisResultRecord, AnalysisResultRecord.analysis_job_id == AnalysisJob.id)
                .where(AnalysisResultRecord.decision == dec_clean)
                .order_by(desc(AnalysisJob.created_at))
                .limit(limit)
                .offset(offset)
            )
            if conditions:
                stmt = stmt.where(*conditions)
            items = self.session.scalars(stmt).all()
        else:
            count_stmt = select(func.count(AnalysisJob.id))
            if conditions:
                count_stmt = count_stmt.where(*conditions)
            total = self.session.scalar(count_stmt) or 0

            stmt = (
                select(AnalysisJob)
                .order_by(desc(AnalysisJob.created_at))
                .limit(limit)
                .offset(offset)
            )
            if conditions:
                stmt = stmt.where(*conditions)
            items = self.session.scalars(stmt).all()

        return items, int(total)

    def get_detail(
        self, identifier: str | uuid.UUID
    ) -> tuple[
        AnalysisJob | None,
        AnalysisResultRecord | None,
        Sequence[DetectorScore],
        Sequence[Alert],
    ]:
        """Retrieves full analysis detail (job, result record, detector scores, alerts).

        Supports lookup by either job UUID or unique request_id.
        """
        job: AnalysisJob | None = None
        if isinstance(identifier, uuid.UUID):
            job = self.session.get(AnalysisJob, identifier)
        else:
            try:
                parsed_uuid = uuid.UUID(str(identifier))
                job = self.session.get(AnalysisJob, parsed_uuid)
            except (ValueError, TypeError):
                pass
            if job is None:
                job = self.get_by_request_id(str(identifier))

        if job is None:
            return None, None, [], []

        result_record = self.session.get(AnalysisResultRecord, job.id)
        scores = self.session.scalars(
            select(DetectorScore)
            .where(DetectorScore.analysis_job_id == job.id)
            .order_by(DetectorScore.detector_code)
        ).all()
        alerts = self.session.scalars(
            select(Alert)
            .where(Alert.analysis_job_id == job.id)
            .order_by(desc(Alert.created_at))
        ).all()

        return job, result_record, scores, alerts

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
            job.completed_at = datetime.now(UTC)
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
