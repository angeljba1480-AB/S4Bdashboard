"""Curated trámites MCP server.

Exposes the curated procedures KB as MCP tools so any agent (ours or a client's)
answers use cases with real local context. The KB is layered:

  - País   : run an instance scoped to a country  -> PAI_MCP_COUNTRY=MX
  - Estado : the same instance filters by region   -> tool arg `region`
  - Empresa: a per-tenant instance adds the company's private layer by calling
             the platform API with a token -> PAI_API_BASE + PAI_TOKEN

So you can run one MCP per country, narrow it by estado, and one per paying
company (with its token) that merges the company-private layer on top.

Run:
    pip install -r requirements-mcp.txt
    PAI_MCP_COUNTRY=MX python -m app.mcp.tramites_server            # country/state
    PAI_API_BASE=https://api... PAI_TOKEN=... python -m app.mcp.tramites_server  # company
"""
from __future__ import annotations

import os

from ..regional.countries import COUNTRIES
from ..regional.tramites import find_tramites, get_tramite, to_context

SCOPE_COUNTRY = os.getenv("PAI_MCP_COUNTRY", "").upper() or None
API_BASE = os.getenv("PAI_API_BASE", "").rstrip("/")
API_TOKEN = os.getenv("PAI_TOKEN", "")


def _company_layer(q: str, region: str | None, municipio: str | None) -> list[dict]:
    """Fetch the paying company's private layer via the platform API (if scoped)."""
    if not (API_BASE and API_TOKEN):
        return []
    import httpx

    params = {k: v for k, v in {"q": q, "region": region, "municipio": municipio}.items() if v}
    try:  # pragma: no cover - network
        r = httpx.get(f"{API_BASE}/tramites", params=params,
                      headers={"Authorization": f"Bearer {API_TOKEN}"}, timeout=20)
        r.raise_for_status()
        return [t for t in r.json() if t.get("source") == "empresa"]
    except Exception:
        return []


def build_server():  # pragma: no cover - requires `mcp` package + runtime
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("tramites-curados")

    @mcp.tool()
    def list_countries() -> list[dict]:
        """Países disponibles y su división (estado/provincia/departamento)."""
        return [{"code": c["code"], "name": c["name"], "division_label": c["division_label"]}
                for c in COUNTRIES]

    @mcp.tool()
    def search_tramites(query: str, country: str = "", region: str = "", municipio: str = "") -> list[dict]:
        """Busca trámites curados por país/estado/municipio. Capa empresa incluida si el server tiene token."""
        ctry = (country or SCOPE_COUNTRY or "MX").upper()
        company = _company_layer(query, region or None, municipio or None)
        curated = find_tramites(ctry, region or None, municipio or None, query or None)
        return company + curated

    @mcp.tool()
    def get_tramite_detail(tramite_id: str) -> dict:
        """Detalle completo de un trámite curado."""
        return get_tramite(tramite_id) or {"error": "no encontrado"}

    @mcp.tool()
    def tramite_context(query: str, country: str = "", region: str = "", municipio: str = "") -> str:
        """Bloque de contexto listo para grounding del agente."""
        ctry = (country or SCOPE_COUNTRY or "MX").upper()
        items = find_tramites(ctry, region or None, municipio or None, query or None)
        return "\n".join(to_context(t) for t in items) or "Sin trámites curados para ese alcance."

    return mcp


def main():  # pragma: no cover
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
