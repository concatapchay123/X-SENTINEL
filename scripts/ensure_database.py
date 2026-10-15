from __future__ import annotations

import os
import time
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text


def main() -> int:
    url = os.getenv("XS_DATABASE_URL")
    if not url:
        print("XS_DATABASE_URL not set; skipping database creation check.")
        return 0

    parsed = urlparse(url)
    if "mssql" not in parsed.scheme:
        print(f"Non-MSSQL dialect ({parsed.scheme}); verifying direct connection.")
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            print("Database connection verified.")
            return 0
        except Exception as exc:
            print(f"Database connection check failed: {exc}")
            return 1

    db_name = parsed.path.lstrip("/") or "xsentinel"
    master_path = "/master"
    master_url = urlunparse(parsed._replace(path=master_path))

    max_attempts = 30
    delay = 2
    for attempt in range(1, max_attempts + 1):
        try:
            engine = create_engine(master_url, pool_pre_ping=True, isolation_level="AUTOCOMMIT")
            with engine.connect() as conn:
                conn.execute(text(f"IF DB_ID('{db_name}') IS NULL CREATE DATABASE [{db_name}];"))
            engine.dispose()
            print(f"Database [{db_name}] verified on attempt {attempt}.")
            return 0
        except Exception as exc:
            if attempt == max_attempts:
                print(f"Failed to ensure database [{db_name}] after {max_attempts} attempts: {exc}")
                return 1
            time.sleep(delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
