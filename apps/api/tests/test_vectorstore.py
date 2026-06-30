"""Vector store: selección de backend + IDs válidos para Qdrant."""
from __future__ import annotations

import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"


def test_inprocess_is_default():
    from app.ai.vectorstore import get_vector_store
    assert get_vector_store() is None  # None = backend in-process


def test_qdrant_point_id_is_valid_uuid_and_deterministic():
    import uuid

    from app.ai.vectorstore import QdrantVectorStore
    pid = QdrantVectorStore._point_id("chk_abc123def456")
    # Debe ser un UUID válido (Qdrant rechaza ids string arbitrarios como 'chk_...').
    assert str(uuid.UUID(pid)) == pid
    # Determinista: el mismo chunk_id siempre mapea al mismo punto (re-upsert sobrescribe).
    assert QdrantVectorStore._point_id("chk_abc123def456") == pid
    assert QdrantVectorStore._point_id("chk_otro") != pid
