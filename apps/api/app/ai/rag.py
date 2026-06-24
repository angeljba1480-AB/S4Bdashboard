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
from ..security.crypto import decrypt, encrypt
from .embeddings import cosine, embed
from .vectorstore import VectorPoint, get_vector_store


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
    """(Re)build chunks + embeddings for a document. Returns chunk count.

    Document and chunk text are encrypted at rest (AES-256-GCM per tenant);
    embeddings are computed on plaintext, chunks are stored as ciphertext.
    """
    existing = session.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    ).all()
    for c in existing:
        session.delete(c)

    plaintext = decrypt(doc.text, doc.tenant_id)
    pieces = chunk_text(plaintext)
    store = get_vector_store()
    points: list[VectorPoint] = []
    for i, piece in enumerate(pieces):
        vec = embed(piece)  # embed plaintext, persist ciphertext
        cipher_piece = encrypt(piece, doc.tenant_id)
        chunk = DocumentChunk(
            tenant_id=doc.tenant_id,
            document_id=doc.id,
            chunk_index=i,
            text=cipher_piece,
            text_hash=hashlib.sha256(piece.encode()).hexdigest(),
            sensitivity=doc.sensitivity,
            embedding=json.dumps(vec),
        )
        session.add(chunk)
        if store:
            points.append(VectorPoint(
                id=chunk.id, vector=vec, document_id=doc.id, chunk_index=i,
                text=cipher_piece, sensitivity=doc.sensitivity.value,
            ))
    doc.text = encrypt(plaintext, doc.tenant_id)  # ensure encrypted at rest
    doc.indexed = True
    session.add(doc)
    session.commit()
    if store and points:
        store.upsert(doc.tenant_id, points)
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
    category: str | None = None,
) -> list[Citation]:
    """Vector search scoped to a tenant (and optionally specific documents or a
    document category — e.g. a recipe grounding only in 'propuesta_comercial')."""
    qvec = embed(query)

    # Category filter: restrict to documents of that category (intersect with
    # explicit document_ids when both are given). An active category with no
    # matching documents yields no results (rather than falling back to all).
    if category:
        cat_ids = [d.id for d in session.exec(
            select(Document).where(Document.tenant_id == tenant_id, Document.category == category)
        ).all()]
        if document_ids:
            allowed = set(document_ids)
            cat_ids = [i for i in cat_ids if i in allowed]
        if not cat_ids:
            return []
        document_ids = cat_ids

    # Managed Qdrant path (when configured); in-process DB path otherwise.
    store = get_vector_store()
    if store:
        docs = {d.id: d for d in session.exec(
            select(Document).where(Document.tenant_id == tenant_id)
        ).all()}
        hits = store.search(tenant_id, qvec, top_k, document_ids)
        return [
            Citation(
                document_id=h.document_id,
                filename=docs[h.document_id].filename if h.document_id in docs else "?",
                chunk_index=h.chunk_index,
                text=decrypt(h.text, tenant_id),
                score=round(h.score, 4),
                sensitivity=Sensitivity(h.sensitivity),
            )
            for h in hits
        ]

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
                text=decrypt(ch.text, tenant_id),
                score=round(score, 4),
                sensitivity=ch.sensitivity,
            )
        )
    # Rerank: highest cosine first (placeholder for a cross-encoder reranker).
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:top_k]
