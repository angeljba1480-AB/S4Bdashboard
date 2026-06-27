"""Resolución de cuenta conectada: la más reciente es la predeterminada."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_most_recent_connection_is_default(client):
    from sqlmodel import Session, select

    from app.db import engine
    from app.integrations import token_store
    from app.models import OAuthToken, Tenant, User

    with Session(engine) as s:
        tenant = s.exec(select(Tenant)).first()
        user = s.exec(select(User).where(User.tenant_id == tenant.id)).first()
        now = datetime.utcnow()
        # Google conectado antes; Microsoft conectado después.
        s.add(OAuthToken(tenant_id=tenant.id, user_id=user.id, provider="google",
                         identifier="viejo@gmail.com", status="active",
                         updated_at=now - timedelta(days=2)))
        s.add(OAuthToken(tenant_id=tenant.id, user_id=user.id, provider="microsoft",
                         identifier="nuevo@outlook.com", status="active",
                         updated_at=now))
        s.commit()

        conns = token_store.list_connections(s, tenant.id, user.id)
        assert conns[0].provider == "microsoft", "la cuenta más reciente debe ir primero"

        # Sin preferencia explícita, resuelve la más reciente (Microsoft).
        chosen = token_store.resolve_connection(s, tenant.id, user.id, "")
        assert chosen.provider == "microsoft" and chosen.identifier == "nuevo@outlook.com"

        # Con preferencia por email, respeta la elección.
        pick = token_store.resolve_connection(s, tenant.id, user.id, "viejo@gmail.com")
        assert pick.provider == "google"
