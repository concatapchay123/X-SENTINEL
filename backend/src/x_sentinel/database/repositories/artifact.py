from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from x_sentinel.database.models import Artifact


class ArtifactRepository:
    """Repository for storing and querying artifact metadata."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, artifact_id: uuid.UUID) -> Artifact | None:
        return self.session.get(Artifact, artifact_id)

    def get_by_sha256(self, sha256: str) -> Sequence[Artifact]:
        stmt = select(Artifact).where(Artifact.sha256 == sha256)
        return self.session.scalars(stmt).all()

    def get_by_job_id(self, analysis_job_id: uuid.UUID) -> Sequence[Artifact]:
        stmt = (
            select(Artifact)
            .where(Artifact.analysis_job_id == analysis_job_id)
            .order_by(Artifact.created_at)
        )
        return self.session.scalars(stmt).all()

    def add(self, artifact: Artifact) -> Artifact:
        self.session.add(artifact)
        self.session.flush()
        return artifact

    def add_many(self, artifacts: list[Artifact]) -> list[Artifact]:
        self.session.add_all(artifacts)
        self.session.flush()
        return artifacts
