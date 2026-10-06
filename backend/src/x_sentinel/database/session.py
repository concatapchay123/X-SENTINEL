from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from x_sentinel.config import settings

_engine_cache: dict[str, Engine] = {}


def get_engine(url: str | None = None) -> Engine:
    target_url = url or settings.database_url
    if target_url not in _engine_cache:
        kwargs: dict[str, object] = {"pool_pre_ping": True}
        if not target_url.startswith("sqlite"):
            kwargs["pool_size"] = settings.db_pool_size
            kwargs["max_overflow"] = settings.db_max_overflow
            kwargs["pool_recycle"] = settings.db_pool_recycle_seconds
        _engine_cache[target_url] = create_engine(target_url, **kwargs)
    return _engine_cache[target_url]


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
