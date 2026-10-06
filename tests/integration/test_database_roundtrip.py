from __future__ import annotations

import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from x_sentinel.database.models import AnalysisJob

pytestmark = [pytest.mark.integration, pytest.mark.db]


@pytest.mark.skipif(not os.getenv("XS_DATABASE_URL"), reason="live DB not configured")
def test_database_is_migrated_and_accepts_job() -> None:
    engine = create_engine(os.environ["XS_DATABASE_URL"])
    request_id = f"ci-{uuid.uuid4()}"
    with Session(engine) as session, session.begin():
        session.add(AnalysisJob(request_id=request_id, status="queued", input_mode="vector", demo_mode=True))
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM analysis_jobs WHERE request_id=:r"), {"r": request_id}).scalar_one() == 1
    engine.dispose()
