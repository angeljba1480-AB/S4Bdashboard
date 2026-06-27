"""Embeddings con NaN: resolución de endpoint (admin→env) y guarda de dimensión."""
from __future__ import annotations

from app.ai import embeddings


def test_cosine_dimension_guard():
    # Vectores de distinta longitud (local 384 ↔ NaN 4096) no deben romper.
    assert embeddings.cosine([1.0, 0.0, 0.0], [1.0, 0.0]) == 0.0
    assert embeddings.cosine([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_embeddings_endpoint_prefers_admin_override(monkeypatch):
    from app.ai import adapters
    from app.config import settings

    monkeypatch.setattr(settings, "embeddings_provider", "open")
    monkeypatch.setattr(adapters, "open_provider_config",
                        lambda: {"base_url": "https://api.nan.builders/v1", "api_key": "sk-x", "model": "qwen3.6"})
    base, key = embeddings._embeddings_endpoint()
    assert base == "https://api.nan.builders/v1" and key == "sk-x"


def test_embed_falls_back_to_local_without_provider(monkeypatch):
    from app.ai import adapters
    from app.config import settings

    monkeypatch.setattr(settings, "embeddings_provider", "open")
    monkeypatch.setattr(settings, "open_base_url", "")
    monkeypatch.setattr(adapters, "open_provider_config", lambda: None)
    vec = embeddings.embed("hola mundo")
    assert len(vec) == settings.embeddings_dim   # cayó al embebedor local
