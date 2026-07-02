"""Alembic: la migración baseline debe aplicar en limpio y NO tener drift contra los
modelos SQLModel (protege contra cambiar un modelo sin crear su migración)."""
from __future__ import annotations

import os
import tempfile

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registra las tablas)

_API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cfg(url: str) -> Config:
    cfg = Config(os.path.join(_API_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(_API_DIR, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_baseline_aplica_y_sin_drift():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite:///{path}"
    try:
        command.upgrade(_cfg(url), "head")  # aplica el baseline en BD vacía
        engine = create_engine(url)
        with engine.connect() as conn:
            mc = MigrationContext.configure(conn, opts={"compare_type": True,
                                                        "render_as_batch": True})
            diffs = compare_metadata(mc, SQLModel.metadata)
        # Solo nos importan diferencias estructurales (tablas/columnas): el baseline
        # debe cubrir el 100% del esquema. Ignoramos matices de tipo/servidor.
        structural = [d for d in diffs if isinstance(d, tuple) and d
                      and d[0] in ("add_table", "remove_table", "add_column", "remove_column")]
        assert structural == [], f"Drift de esquema (falta migración): {structural}"
    finally:
        os.remove(path)
