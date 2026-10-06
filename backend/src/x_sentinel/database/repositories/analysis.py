from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from x_sentinel.database.models import AnalysisJob


class AnalysisJobRepository:
    """Persistence skeleton. Business services must use repositories, not raw SQL."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_request_id(self, request_id: str) -> AnalysisJob | None:
        return self.session.scalar(select(AnalysisJob).where(AnalysisJob.request_id == request_id))

    def add(self, job: AnalysisJob) -> AnalysisJob:
        self.session.add(job)
        self.session.flush()
        return job
