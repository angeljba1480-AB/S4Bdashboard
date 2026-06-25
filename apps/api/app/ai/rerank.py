"""Cross-encoder reranking for RAG (NaN `/rerank`, Qwen3-Reranker-8B).

After embedding retrieval gives top-K candidates, we reorder them by true
query↔document relevance with a reranker, then keep the best top_n. Uses the
**open** provider's base_url + API key (OpenAI-compatible host). No-ops (returns
None) when disabled or unconfigured, so callers fall back to cosine order.

See docs/PROVEEDOR-NAN.md — `/v1/rerank` returns
`{results: [{index, relevance_score, ...}]}`.
"""
from __future__ import annotations

from ..config import settings
from .images import _open_provider  # reuse open-provider resolution (admin → env)

TIMEOUT = 30


def is_enabled() -> bool:
    from .. import runtime_config

    return runtime_config.rerank_enabled() and _open_provider() is not None


def rerank(query: str, documents: list[str], top_n: int | None = None) -> list[int] | None:  # pragma: no cover - network
    """Return document indices ordered by relevance (best first), or None if the
    reranker is unavailable/fails so the caller keeps its original order."""
    import httpx

    if not query or not documents:
        return None
    prov = _open_provider()
    if not prov:
        return None
    base = prov["base_url"].rstrip("/")
    body = {"model": settings.rerank_model, "query": query, "documents": documents}
    if top_n:
        body["top_n"] = top_n
    try:
        r = httpx.post(f"{base}/rerank", headers={"Authorization": f"Bearer {prov['api_key']}"},
                       json=body, timeout=TIMEOUT)
        r.raise_for_status()
        results = r.json().get("results", [])
        order = [int(item["index"]) for item in results if "index" in item]
        # Keep only valid indices; append any missing (defensive) to not drop docs.
        seen = set(order)
        order += [i for i in range(len(documents)) if i not in seen]
        return [i for i in order if 0 <= i < len(documents)]
    except Exception:
        return None
