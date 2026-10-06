from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

pytestmark = [pytest.mark.integration, pytest.mark.db]


@pytest.mark.skipif(not os.getenv("XS_DATABASE_URL"), reason="live DB not configured")
def test_database_revision_matches_expected() -> None:
    engine = create_engine(os.environ["XS_DATABASE_URL"])
    with engine.connect() as conn:
        current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    engine.dispose()
    assert current == os.getenv("XS_EXPECTED_DB_REVISION", "0002_v3_jev_ai_audit")
