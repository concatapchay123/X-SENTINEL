from __future__ import annotations

import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from x_sentinel.config import settings
from x_sentinel.database.models import AnalysisJob

pytestmark = [pytest.mark.integration, pytest.mark.db]


def _get_db_url() -> str | None:
    candidate = os.getenv("XS_DATABASE_URL", settings.database_url)
    try:
        engine = create_engine(candidate)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return candidate
    except Exception:
        return None


_db_url = _get_db_url()


@pytest.mark.skipif(_db_url is None, reason="live DB not reachable")
def test_database_is_migrated_and_accepts_job() -> None:
    assert _db_url is not None
    engine = create_engine(_db_url)
    request_id = f"ci-{uuid.uuid4()}"
    try:
        with Session(engine) as session, session.begin():
            session.add(AnalysisJob(request_id=request_id, status="queued", input_mode="vector", demo_mode=True))
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM analysis_jobs WHERE request_id=:r"), {"r": request_id}).scalar_one() == 1
    finally:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM analysis_jobs WHERE request_id=:r"), {"r": request_id})
            conn.commit()
        engine.dispose()
