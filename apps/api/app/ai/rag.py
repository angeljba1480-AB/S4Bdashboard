"""RAG layer: chunking, indexing, retrieval, reranking and citations.

Uses an in-process vector store backed by the document_chunks table (embeddings
stored as JSON). The retrieval/cosine interface mirrors what a Qdrant/pgvector
backend would expose, so it can be swapped without touching callers.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlmodel import Session, select

from ..models import Document, DocumentChunk, Sensitivity
from .embeddings import cosine, embed


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def index_document(session: Session, doc: Document) -> int:
    """(Re)build chunks + embeddings for a document. Returns chunk count."""
    existing = session.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    ).all()
    for c in existing:
        session.delete(c)

    pieces = chunk_text(doc.text)
    for i, piece in enumerate(pieces):
        vec = embed(piece)
        session.add(
            DocumentChunk(
                tenant_id=doc.tenant_id,
                document_id=doc.id,
                chunk_index=i,
                text=piece,
                text_hash=hashlib.sha256(piece.encode()).hexdigest(),
                sensitivity=doc.sensitivity,
                embedding=json.dumps(vec),
            )
        )
    doc.indexed = True
    session.add(doc)
    session.commit()
    return len(pieces)


@dataclass
class Citation:
    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float
    sensitivity: Sensitivity


def retrieve(
    session: Session,
    tenant_id: str,
    query: str,
    document_ids: list[str] | None = None,
    top_k: int = 4,
) -> list[Citation]:
    """Vector search scoped to a tenant (and optionally specific documents)."""
    qvec = embed(query)
    stmt = select(DocumentChunk).where(DocumentChunk.tenant_id == tenant_id)
    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))
    chunks = session.exec(stmt).all()
    if not chunks:
        return []

    docs = {d.id: d for d in session.exec(
        select(Document).where(Document.tenant_id == tenant_id)
    ).all()}

    scored: list[Citation] = []
    for ch in chunks:
        try:
            vec = json.loads(ch.embedding)
        except (json.JSONDecodeError, TypeError):
            continue
        score = cosine(qvec, vec)
        doc = docs.get(ch.document_id)
        scored.append(
            Citation(
                document_id=ch.document_id,
                filename=doc.filename if doc else "?",
                chunk_index=ch.chunk_index,
                text=ch.text,
                score=round(score, 4),
                sensitivity=ch.sensitivity,
            )
        )
    # Rerank: highest cosine first (placeholder for a cross-encoder reranker).
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:top_k]
