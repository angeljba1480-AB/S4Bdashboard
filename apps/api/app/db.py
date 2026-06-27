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


def _ensure_columns() -> None:
    """Additive, idempotent migration for columns added after a table's first
    create (create_all never ALTERs existing tables). Safe on SQLite + Postgres."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    plan: dict[str, dict[str, str]] = {
        "documents": {"area": "''", "category": "''"},
        "users": {"area": "''", "license": "'basic'", "mfa_secret_enc": "''", "mfa_backup_codes": "''"},
        "n8n_recipes": {"provider": "'n8n'", "webhook_url": "''"},
    }
    with engine.begin() as conn:
        for table, cols in plan.items():
            if table not in tables:
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for col, default in cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} VARCHAR DEFAULT {default}"))


def init_db() -> None:
    # Import models so SQLModel registers the tables before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _ensure_columns()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
