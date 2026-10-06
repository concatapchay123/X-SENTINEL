from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from x_sentinel.config import settings
from x_sentinel.database.session import get_engine


@dataclass(frozen=True)
class DatabaseHealth:
    ok: bool
    reachable: bool
    current_revision: str | None
    expected_revision: str
    error: str | None = None
    status: str = "ready"
    revision_status: str = "current"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def classify_revision_status(current_rev: str | None, expected_rev: str) -> str:
    """Classify the relationship between current DB revision and expected head revision.

    Returns one of:
    - 'unmigrated': if current_rev is None or empty.
    - 'current': if current_rev matches expected_rev.
    - 'behind': if current_rev is an ancestor of expected_rev.
    - 'ahead': if expected_rev is an ancestor of current_rev.
    - 'unknown': if current_rev is not in Alembic revision history.
    - 'mismatch': if both exist but neither is an ancestor.
    """
    if not current_rev:
        return "unmigrated"
    if current_rev == expected_rev:
        return "current"

    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config("database/alembic.ini")
        script = ScriptDirectory.from_config(cfg)

        try:
            script.get_revision(current_rev)
        except Exception:
            return "unknown"

        # Walk downward from expected_rev to check if current_rev is behind
        curr: str | None = expected_rev
        while curr:
            sc = script.get_revision(curr)
            if not sc:
                break
            if sc.down_revision == current_rev:
                return "behind"
            curr = sc.down_revision

        # Walk downward from current_rev to check if current_rev is ahead
        curr = current_rev
        while curr:
            sc = script.get_revision(curr)
            if not sc:
                break
            if sc.down_revision == expected_rev:
                return "ahead"
            curr = sc.down_revision

        return "mismatch"
    except Exception:
        return "mismatch"


def database_health(engine_override: Engine | None = None) -> DatabaseHealth:
    """Inspect database connectivity and migration revision state.

    Hard boundaries:
    1. NEVER execute migrations ('alembic upgrade head') inside readiness checks.
    2. NEVER leak connection URLs, passwords, or raw exception tracebacks.
    3. Accurately report whether the database is unreachable vs unmigrated vs mismatched.
    """
    eng = engine_override or get_engine()
    expected_rev = settings.expected_db_revision

    # Phase 1: Test connectivity
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return DatabaseHealth(
            ok=False,
            reachable=False,
            current_revision=None,
            expected_revision=expected_rev,
            status="unavailable",
            revision_status="unknown",
            error=f"{type(exc).__name__}: database connection failed",
        )
    except Exception as exc:
        return DatabaseHealth(
            ok=False,
            reachable=False,
            current_revision=None,
            expected_revision=expected_rev,
            status="unavailable",
            revision_status="unknown",
            error=f"{type(exc).__name__}: database unavailable",
        )

    # Phase 2: Inspect alembic_version table
    try:
        with eng.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            current_rev = str(row) if row is not None else None
    except SQLAlchemyError as exc:
        # DB is reachable, but alembic_version table is absent or unmigrated
        return DatabaseHealth(
            ok=False,
            reachable=True,
            current_revision=None,
            expected_revision=expected_rev,
            status="not_ready",
            revision_status="unmigrated",
            error=f"{type(exc).__name__}: migration table alembic_version absent or unmigrated",
        )

    rev_status = classify_revision_status(current_rev, expected_rev)
    if rev_status == "current":
        return DatabaseHealth(
            ok=True,
            reachable=True,
            current_revision=current_rev,
            expected_revision=expected_rev,
            status="ready",
            revision_status="current",
            error=None,
        )
    elif rev_status == "unmigrated":
        return DatabaseHealth(
            ok=False,
            reachable=True,
            current_revision=current_rev,
            expected_revision=expected_rev,
            status="not_ready",
            revision_status="unmigrated",
            error="database migration revision missing: database is unmigrated",
        )
    elif rev_status == "behind":
        return DatabaseHealth(
            ok=False,
            reachable=True,
            current_revision=current_rev,
            expected_revision=expected_rev,
            status="not_ready",
            revision_status="behind",
            error="database migration revision mismatch: database is behind expected head",
        )
    elif rev_status == "ahead":
        return DatabaseHealth(
            ok=False,
            reachable=True,
            current_revision=current_rev,
            expected_revision=expected_rev,
            status="not_ready",
            revision_status="ahead",
            error="database migration revision mismatch: database is ahead of expected head",
        )
    else:
        return DatabaseHealth(
            ok=False,
            reachable=True,
            current_revision=current_rev,
            expected_revision=expected_rev,
            status="not_ready",
            revision_status=rev_status,
            error=f"database migration revision mismatch: revision '{current_rev}' is {rev_status}",
        )
