"""Model adapters.

A uniform interface over every backing model. The MOCK adapter always works
with zero configuration so the platform runs end-to-end; OpenAI-compatible
adapters (premium / open / vpc / local-Ollama) are used when enabled in config.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import settings
from ..models import ModelRoute


@dataclass
class ModelResponse:
    content: str
    model: str
    provider: str


class ModelAdapter:
    route: ModelRoute
    enabled: bool = True
    model_name: str = "mock"

    def generate(self, system: str, prompt: str, context: list[str]) -> ModelResponse:
        raise NotImplementedError


class MockAdapter(ModelAdapter):
    """Deterministic offline adapter: grounds its answer in the given context."""

    def __init__(self, route: ModelRoute, label: str):
        self.route = route
        self.model_name = f"mock-{label}"

    def generate(self, system: str, prompt: str, context: list[str]) -> ModelResponse:
        if context:
            joined = "\n".join(f"- {c[:160]}" for c in context[:3])
            body = (
                f"**Respuesta basada en {len(context)} fragmento(s) recuperados:**\n\n"
                f"{joined}\n\n"
                f"_(Generado por el modelo {self.model_name} sobre la ruta "
                f"`{self.route.value}`. Configura un proveedor real en .env para "
                f"respuestas completas.)_"
            )
        else:
            body = (
                f"No se recuperaron documentos para «{prompt[:80]}». "
                f"Respuesta general del modelo `{self.model_name}` "
                f"(ruta `{self.route.value}`)."
            )
        return ModelResponse(content=body, model=self.model_name, provider="mock")


class OpenAICompatAdapter(ModelAdapter):
    """Works with OpenAI, OpenRouter, vLLM, TGI and Ollama (/v1) endpoints."""

    def __init__(self, route: ModelRoute, base_url: str, api_key: str, model: str):
        self.route = route
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model

    def generate(self, system: str, prompt: str, context: list[str]) -> ModelResponse:  # pragma: no cover - network
        import httpx

        ctx = "\n\n".join(context)
        user = f"Contexto:\n{ctx}\n\nPregunta: {prompt}" if ctx else prompt
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system or "Eres un asistente empresarial."},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return ModelResponse(content=content, model=self.model_name, provider=self.base_url)


def get_adapter(route: ModelRoute) -> ModelAdapter:
    """Resolve the configured adapter for a route, falling back to MOCK."""
    cfg = {
        ModelRoute.PREMIUM: (settings.premium_enabled, settings.premium_base_url, settings.premium_api_key, settings.premium_model),
        ModelRoute.OPEN: (settings.open_enabled, settings.open_base_url, settings.open_api_key, settings.open_model),
        ModelRoute.VPC: (settings.vpc_enabled, settings.vpc_base_url, settings.vpc_api_key, settings.vpc_model),
        ModelRoute.LOCAL: (settings.local_enabled, settings.local_base_url, "ollama", settings.local_model),
    }.get(route)

    if cfg and cfg[0]:
        _, base, key, model = cfg
        return OpenAICompatAdapter(route, base, key, model)
    return MockAdapter(route, route.value)
