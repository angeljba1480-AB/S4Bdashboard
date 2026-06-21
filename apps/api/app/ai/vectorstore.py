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
        from qdrant_client import QdrantClient  # imported lazily

        self._client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        self._Distance = __import__("qdrant_client.models", fromlist=["Distance"]).Distance
        self._VectorParams = __import__("qdrant_client.models", fromlist=["VectorParams"]).VectorParams
        self._PointStruct = __import__("qdrant_client.models", fromlist=["PointStruct"]).PointStruct

    def _collection(self, tenant_id: str) -> str:
        return f"tenant_{tenant_id}"

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
                    id=p.id,
                    vector=p.vector,
                    payload={
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


_store: QdrantVectorStore | None = None


def get_vector_store() -> QdrantVectorStore | None:
    """Return the Qdrant store if configured, else ``None`` (use in-process)."""
    global _store
    if settings.vector_store != "qdrant":
        return None
    if _store is None:
        _store = QdrantVectorStore()
    return _store
