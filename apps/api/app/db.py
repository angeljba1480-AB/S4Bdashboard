"""Database engine and session helpers (SQLModel)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import settings


def _normalize(url: str) -> str:
    # Managed providers (Render/Heroku) hand out postgres://, which SQLAlchemy 2
    # no longer accepts. Normalize to the psycopg2 dialect.
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = _normalize(settings.database_url)
_is_sqlite = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if _is_sqlite else {}
# pool_pre_ping avoids stale connections on managed Postgres (Supabase/Render).
engine = create_engine(
    DATABASE_URL, echo=False, connect_args=connect_args,
    pool_pre_ping=not _is_sqlite,
)


def init_db() -> None:
    # Import models so SQLModel registers the tables before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
