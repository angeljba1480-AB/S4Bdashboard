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
        "users": {"area": "''", "license": "'basic'", "mfa_secret_enc": "''", "mfa_backup_codes": "''",
                  "callmebot_phone": "''", "callmebot_apikey_enc": "''"},
        "n8n_recipes": {"provider": "'n8n'", "webhook_url": "''"},
        "alert_rules": {"schedule": "''", "last_digest_at": "''"},
        "company_profiles": {"org_type": "'privada'", "gov_tramites": "''"},
        "tenants": {"support_account_id": "''", "support_from": "''", "support_from_name": "''",
                    "custom_domain": "''"},
    }
    with engine.begin() as conn:
        for table, cols in plan.items():
            if table not in tables:
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for col, default in cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} VARCHAR DEFAULT {default}"))


def _alembic_upgrade() -> None:
    """Producción: Alembic es la fuente de verdad del esquema.

    - BD nueva (sin tablas): aplica todas las migraciones.
    - BD legacy (tablas creadas con create_all, sin control de versión): la sella en el
      baseline y luego aplica lo pendiente, sin recrear tablas existentes.
    """
    import os

    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect

    api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(api_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(api_dir, "migrations"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if tables and "alembic_version" not in tables:
        # Esquema legacy (creado con create_all, ~= baseline) → sellarlo EN el baseline
        # (revisión raíz) para no recrear tablas; luego aplicar migraciones posteriores.
        base_rev = ScriptDirectory.from_config(cfg).get_bases()[0]
        command.stamp(cfg, base_rev)
    command.upgrade(cfg, "head")


def init_db() -> None:
    # Import models so SQLModel registers the tables.
    from . import models  # noqa: F401

    if settings.is_production:
        _alembic_upgrade()
        return
    # Dev/tests: create_all es rápido y suficiente (Alembic se prueba aparte).
    SQLModel.metadata.create_all(engine)
    _ensure_columns()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
