from __future__ import annotations

from typing import Sequence
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from x_sentinel.database.models import DetectorScore


class DetectorScoreRepository:
    """Repository for M1-M5 detector scores per analysis job."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_job_id(self, analysis_job_id: uuid.UUID) -> Sequence[DetectorScore]:
        stmt = (
            select(DetectorScore)
            .where(DetectorScore.analysis_job_id == analysis_job_id)
            .order_by(DetectorScore.detector_code)
        )
        return self.session.scalars(stmt).all()

    def get_by_job_and_detector(
        self,
        analysis_job_id: uuid.UUID,
        detector_code: str,
    ) -> DetectorScore | None:
        return self.session.get(DetectorScore, (analysis_job_id, detector_code))

    def add(self, score: DetectorScore) -> DetectorScore:
        self.session.add(score)
        self.session.flush()
        return score

    def add_many(self, scores: list[DetectorScore]) -> list[DetectorScore]:
        self.session.add_all(scores)
        self.session.flush()
        return scores
