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
        # Self-hosted routes (local Ollama / VPC) load the model then generate on
        # CPU/GPU, so they need a longer timeout than the fast cloud routes.
        timeout = (
            settings.local_request_timeout
            if self.route in (ModelRoute.LOCAL, ModelRoute.VPC)
            else settings.model_request_timeout
        )
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
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return ModelResponse(content=content, model=self.model_name, provider=self.base_url)


# Runtime overrides set from the admin UI (global), take precedence over env.
# Shape: {route_value: {"enabled","base_url","model","api_key"}}
_RUNTIME: dict[str, dict] = {}


def set_runtime_override(route_value: str, cfg: dict | None) -> None:
    if cfg is None:
        _RUNTIME.pop(route_value, None)
    else:
        _RUNTIME[route_value] = cfg


def load_overrides(session) -> None:
    """Load admin-configured external providers from the DB into the runtime cache."""
    from ..models import ProviderSetting
    from ..security.crypto import decrypt
    from sqlmodel import select

    _RUNTIME.clear()
    for row in session.exec(select(ProviderSetting)).all():
        key = decrypt(row.api_key_enc, settings.secret_key) if row.api_key_enc else ""
        _RUNTIME[row.route] = {"enabled": row.enabled, "base_url": row.base_url,
                               "model": row.model, "api_key": key}


def get_adapter(route: ModelRoute) -> ModelAdapter:
    """Resolve the configured adapter for a route, falling back to MOCK.

    Order: admin UI runtime override → env settings → MOCK.
    """
    ov = _RUNTIME.get(route.value)
    if ov and ov.get("enabled") and ov.get("base_url"):
        return OpenAICompatAdapter(route, ov["base_url"], ov.get("api_key", ""),
                                   ov.get("model") or route.value)

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
