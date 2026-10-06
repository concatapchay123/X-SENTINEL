from __future__ import annotations

import os
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text


def main() -> int:
    cfg = Config("database/alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) != 1:
        print(f"BLOCKED: expected exactly one Alembic head, found {heads}")
        return 2
    expected = os.getenv("XS_EXPECTED_DB_REVISION", heads[0])
    if expected != heads[0]:
        print(f"BLOCKED: XS_EXPECTED_DB_REVISION={expected} but repo head={heads[0]}")
        return 3
    url = os.getenv("XS_DATABASE_URL")
    if not url:
        print(f"repo schema head OK: {heads[0]} (DB check skipped; XS_DATABASE_URL not set)")
        return 0
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    finally:
        engine.dispose()
    if current != heads[0]:
        print(f"BLOCKED: database revision={current}; repo head={heads[0]}")
        return 4
    print(f"database schema revision OK: {current}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
