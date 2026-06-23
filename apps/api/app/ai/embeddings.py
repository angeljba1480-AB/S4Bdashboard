"""Embeddings.

Default = a deterministic local embedder (hashing bag-of-words) so the whole
RAG pipeline runs with zero external calls. Swappable for a real provider by
setting EMBEDDINGS_PROVIDER and implementing the same `embed()` signature.
"""
from __future__ import annotations

import hashlib
import math
import re

import numpy as np

from ..config import settings

_TOKEN_RE = re.compile(r"[a-záéíóúñ0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _local_embed(text: str, dim: int) -> list[float]:
    """Hashing vectorizer with L2 normalization — stable and dependency-free."""
    vec = np.zeros(dim, dtype=np.float32)
    for tok in _tokenize(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec.tolist()


def embed(text: str) -> list[float]:
    if settings.embeddings_provider == "local":
        return _local_embed(text, settings.embeddings_dim)

    # Real provider (OpenAI-compatible). "open"/"nan" -> NaN Builders endpoint,
    # "premium" -> premium endpoint. Falls back to local embedder on any error.
    base, key = _embeddings_endpoint()
    try:  # pragma: no cover - network path
        import httpx

        resp = httpx.post(
            f"{base.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": settings.embeddings_model, "input": text},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception:
        return _local_embed(text, settings.embeddings_dim)


def _embeddings_endpoint() -> tuple[str, str]:
    provider = settings.embeddings_provider
    if provider in ("open", "nan", "nanbuilders"):
        return settings.open_base_url, settings.open_api_key
    return settings.premium_base_url, settings.premium_api_key


def cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))
