from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from x_sentinel.config import settings
from x_sentinel.database.session import engine


@dataclass(frozen=True)
class DatabaseHealth:
    ok: bool
    reachable: bool
    current_revision: str | None
    expected_revision: str
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def database_health() -> DatabaseHealth:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        return DatabaseHealth(
            ok=revision == settings.expected_db_revision,
            reachable=True,
            current_revision=revision,
            expected_revision=settings.expected_db_revision,
            error=None if revision == settings.expected_db_revision else "database migration revision mismatch",
        )
    except SQLAlchemyError as exc:
        return DatabaseHealth(
            ok=False,
            reachable=False,
            current_revision=None,
            expected_revision=settings.expected_db_revision,
            error=f"{type(exc).__name__}: database unavailable or not migrated",
        )
