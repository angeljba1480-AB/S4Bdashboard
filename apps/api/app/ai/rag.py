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

from ..config import settings
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
    areas: list[str] | None = None,
) -> list[Citation]:
    """Vector search scoped to a tenant (and optionally specific documents, a
    document category, or the areas a user is allowed to see).

    `areas=None` means no area restriction (privileged roles); a list restricts
    to documents in those areas plus general/unassigned ones (area == "").
    """
    qvec = embed(query)

    # Narrow the candidate documents by category and/or area visibility. Each
    # active filter intersects with any explicit document_ids; if the result is
    # empty we return nothing (rather than falling back to the whole tenant).
    if category is not None or areas is not None:
        q = select(Document).where(Document.tenant_id == tenant_id)
        if category:
            q = q.where(Document.category == category)
        candidates = session.exec(q).all()
        if areas is not None:
            allowed_areas = set(areas)
            candidates = [d for d in candidates if not (d.area or "") or d.area in allowed_areas]
        ids = [d.id for d in candidates]
        if document_ids:
            keep = set(document_ids)
            ids = [i for i in ids if i in keep]
        if not ids:
            return []
        document_ids = ids

    # How many candidates to pull before reranking down to top_k.
    from .rerank import is_enabled as rerank_on
    use_rerank = rerank_on()
    fetch_k = max(top_k, settings.rerank_candidates) if use_rerank else top_k

    # Managed Qdrant path (when configured); in-process DB path otherwise.
    store = get_vector_store()
    if store:
        docs = {d.id: d for d in session.exec(
            select(Document).where(Document.tenant_id == tenant_id)
        ).all()}
        hits = store.search(tenant_id, qvec, fetch_k, document_ids)
        cites = [
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
        return _maybe_rerank(query, cites, top_k, use_rerank)

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
    # Order by cosine first, then optionally rerank the top candidates.
    scored.sort(key=lambda c: c.score, reverse=True)
    return _maybe_rerank(query, scored[:fetch_k], top_k, use_rerank)


def _maybe_rerank(query: str, cites: list[Citation], top_k: int, use_rerank: bool) -> list[Citation]:
    """Reorder candidates with the cross-encoder reranker when enabled; otherwise
    keep the cosine order. Falls back to cosine order if the reranker fails."""
    if not use_rerank or len(cites) <= 1:
        return cites[:top_k]
    from .rerank import rerank
    order = rerank(query, [c.text for c in cites], top_n=top_k)
    if not order:
        return cites[:top_k]
    return [cites[i] for i in order[:top_k]]
