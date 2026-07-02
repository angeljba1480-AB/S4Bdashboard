"""Entorno de Alembic — usa la metadata de SQLModel y la URL de settings.

La URL de la BD viene de la app (``settings.database_url``), no de alembic.ini, para
no duplicar credenciales ni fijar SQLite. `target_metadata` son los modelos SQLModel,
de modo que `alembic revision --autogenerate` detecte cambios de esquema reales.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Registra todas las tablas importando los modelos ANTES de leer la metadata.
from app import models  # noqa: F401
from app.config import settings
from sqlmodel import SQLModel

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL: respeta una ya inyectada en la config (p. ej. desde un test), si no, la de settings.
_url = config.get_main_option("sqlalchemy.url") or settings.database_url
config.set_main_option("sqlalchemy.url", _url)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=_url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _url
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # batch mode para que ALTER funcione también en SQLite (dev).
            render_as_batch=_url.startswith("sqlite"),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
