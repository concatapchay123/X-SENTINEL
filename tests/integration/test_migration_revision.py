from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from x_sentinel.config import settings

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
def test_database_revision_matches_expected() -> None:
    assert _db_url is not None
    engine = create_engine(_db_url)
    with engine.connect() as conn:
        current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    engine.dispose()
    assert current == os.getenv("XS_EXPECTED_DB_REVISION", "0002_v3_jev_ai_audit")
