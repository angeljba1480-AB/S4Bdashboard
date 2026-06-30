"""Pluggable vector store (blueprint §4: RAG layer = Qdrant/pgvector).

Default backend is ``inprocess`` (embeddings live in the document_chunks table,
cosine in Python) so the platform runs with zero infra. Set ``VECTOR_STORE=qdrant``
to use a managed Qdrant — the in-process path stays the fallback. Both expose the
same ``upsert``/``search`` surface so callers (``rag.py``) are backend-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import settings


@dataclass
class VectorHit:
    document_id: str
    chunk_index: int
    text: str          # ciphertext at rest; decrypted by the caller
    sensitivity: str
    score: float


@dataclass
class VectorPoint:
    id: str
    vector: list[float]
    document_id: str
    chunk_index: int
    text: str
    sensitivity: str


class QdrantVectorStore:
    """Qdrant-backed store, one collection per tenant (lazy client import)."""

    def __init__(self) -> None:
        try:
            from qdrant_client import QdrantClient  # imported lazily
        except ImportError as exc:  # turnkey: mensaje claro si falta el cliente
            raise RuntimeError(
                "VECTOR_STORE=qdrant pero falta el paquete: instala 'qdrant-client' "
                "(pip install qdrant-client) o usa VECTOR_STORE=pgvector.") from exc

        self._client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        self._Distance = __import__("qdrant_client.models", fromlist=["Distance"]).Distance
        self._VectorParams = __import__("qdrant_client.models", fromlist=["VectorParams"]).VectorParams
        self._PointStruct = __import__("qdrant_client.models", fromlist=["PointStruct"]).PointStruct

    def _collection(self, tenant_id: str) -> str:
        return f"tenant_{tenant_id}"

    @staticmethod
    def _point_id(chunk_id: str) -> str:
        # Qdrant exige id entero o UUID; nuestros chunk ids son 'chk_<hex>'.
        # uuid5 determinista → re-upsert sobrescribe el mismo punto.
        import uuid
        return str(uuid.uuid5(uuid.NAMESPACE_OID, chunk_id))

    def ensure_collection(self, tenant_id: str) -> None:
        name = self._collection(tenant_id)
        if not self._client.collection_exists(name):
            self._client.create_collection(
                name,
                vectors_config=self._VectorParams(size=settings.embeddings_dim, distance=self._Distance.COSINE),
            )

    def upsert(self, tenant_id: str, points: list[VectorPoint]) -> None:
        self.ensure_collection(tenant_id)
        self._client.upsert(
            self._collection(tenant_id),
            points=[
                self._PointStruct(
                    id=self._point_id(p.id),
                    vector=p.vector,
                    payload={
                        "chunk_id": p.id,
                        "document_id": p.document_id,
                        "chunk_index": p.chunk_index,
                        "text": p.text,
                        "sensitivity": p.sensitivity,
                    },
                )
                for p in points
            ],
        )

    def delete_document(self, tenant_id: str, document_id: str) -> None:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        self._client.delete(
            self._collection(tenant_id),
            points_selector=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]),
        )

    def search(
        self, tenant_id: str, query: list[float], top_k: int, document_ids: list[str] | None = None
    ) -> list[VectorHit]:
        flt = None
        if document_ids:
            from qdrant_client.models import FieldCondition, Filter, MatchAny

            flt = Filter(must=[FieldCondition(key="document_id", match=MatchAny(any=document_ids))])
        res = self._client.search(self._collection(tenant_id), query_vector=query, limit=top_k, query_filter=flt)
        return [
            VectorHit(
                document_id=r.payload["document_id"],
                chunk_index=r.payload["chunk_index"],
                text=r.payload["text"],
                sensitivity=r.payload.get("sensitivity", "internal"),
                score=float(r.score),
            )
            for r in res
        ]


class PgVectorVectorStore:
    """Supabase / Postgres + pgvector backend (one shared table, tenant-scoped).

    Lets a single Supabase Postgres serve as both the relational store and the
    RAG vector DB — no separate Qdrant. Uses raw SQL via the app's engine.
    """

    def __init__(self) -> None:
        from ..db import engine  # reuse the configured DATABASE_URL

        self._engine = engine
        self._dim = settings.embeddings_dim
        self.ensure_schema()

    def _vec(self, v: list[float]) -> str:
        return "[" + ",".join(repr(float(x)) for x in v) + "]"

    def ensure_schema(self) -> None:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text(
                f"CREATE TABLE IF NOT EXISTS rag_chunks ("
                f"  id text PRIMARY KEY, tenant_id text NOT NULL, document_id text NOT NULL,"
                f"  chunk_index int NOT NULL, text text NOT NULL, sensitivity text NOT NULL,"
                f"  embedding vector({self._dim}))"
            ))
            conn.execute(text("CREATE INDEX IF NOT EXISTS rag_chunks_tenant ON rag_chunks(tenant_id)"))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS rag_chunks_embedding ON rag_chunks "
                "USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)"
            ))

    def upsert(self, tenant_id: str, points: list[VectorPoint]) -> None:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            for p in points:
                conn.execute(
                    text(
                        "INSERT INTO rag_chunks (id, tenant_id, document_id, chunk_index, text, sensitivity, embedding) "
                        "VALUES (:id, :t, :d, :i, :x, :s, :e) "
                        "ON CONFLICT (id) DO UPDATE SET text=:x, sensitivity=:s, embedding=:e"
                    ),
                    {"id": p.id, "t": tenant_id, "d": p.document_id, "i": p.chunk_index,
                     "x": p.text, "s": p.sensitivity, "e": self._vec(p.vector)},
                )

    def delete_document(self, tenant_id: str, document_id: str) -> None:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM rag_chunks WHERE tenant_id=:t AND document_id=:d"),
                         {"t": tenant_id, "d": document_id})

    def search(
        self, tenant_id: str, query: list[float], top_k: int, document_ids: list[str] | None = None
    ) -> list[VectorHit]:
        from sqlalchemy import text

        sql = ("SELECT document_id, chunk_index, text, sensitivity, "
               "1 - (embedding <=> :q) AS score FROM rag_chunks WHERE tenant_id=:t ")
        params: dict = {"q": self._vec(query), "t": tenant_id, "k": top_k}
        if document_ids:
            sql += "AND document_id = ANY(:docs) "
            params["docs"] = document_ids
        sql += "ORDER BY embedding <=> :q LIMIT :k"
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
        return [
            VectorHit(document_id=r[0], chunk_index=r[1], text=r[2], sensitivity=r[3], score=float(r[4]))
            for r in rows
        ]


_store: QdrantVectorStore | PgVectorVectorStore | None = None


def get_vector_store() -> QdrantVectorStore | PgVectorVectorStore | None:
    """Return the configured store, or ``None`` to use the in-process backend."""
    global _store
    if settings.vector_store == "qdrant":
        if not isinstance(_store, QdrantVectorStore):
            _store = QdrantVectorStore()
        return _store
    if settings.vector_store == "pgvector":
        if not isinstance(_store, PgVectorVectorStore):
            _store = PgVectorVectorStore()
        return _store
    return None
