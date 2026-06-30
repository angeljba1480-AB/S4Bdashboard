"""Lector OData (SAP S/4HANA y compatibles) de SOLO lectura.

Hace GET a un Entity Set de OData y devuelve (columnas, filas) para importarlas
al repositorio + RAG / tablero. Soporta OData v2 (``d.results``) y v4 (``value``),
auth Basic o Bearer, y paginación por ``__next`` / ``@odata.nextLink``.

Las LECTURAS no requieren X-CSRF-Token (eso aplica solo a escrituras). El cliente
es deliberadamente de solo lectura: nunca hace POST/PUT/DELETE.
"""
from __future__ import annotations

MAX_ROWS = 1000
MAX_PAGES = 20
SCALAR = (str, int, float, bool, type(None))


def _rows_from_payload(payload: dict) -> tuple[list[dict], str | None]:
    """Extrae las filas y el link a la siguiente página de una respuesta OData."""
    if not isinstance(payload, dict):
        return [], None
    # v4
    if "value" in payload and isinstance(payload["value"], list):
        return payload["value"], payload.get("@odata.nextLink")
    # v2: {"d": {"results": [...], "__next": "..."}} o {"d": {...}}
    d = payload.get("d")
    if isinstance(d, dict):
        if isinstance(d.get("results"), list):
            return d["results"], d.get("__next")
        return [d], None
    if isinstance(d, list):
        return d, None
    return [], None


def _flatten(row: dict) -> dict:
    """Deja solo campos escalares (omite __metadata y objetos anidados/deferred)."""
    out: dict = {}
    for k, v in row.items():
        if k == "__metadata":
            continue
        out[k] = v if isinstance(v, SCALAR) else ""
    return out


def fetch(base_url: str, *, auth_type: str = "basic", username: str = "", secret: str = "",
          odata_filter: str = "", select: str = "", top: int = 0,
          max_rows: int = MAX_ROWS) -> tuple[list[str], list[tuple]]:
    """GET a un Entity Set OData → (columnas, filas). Lanza excepción en error HTTP."""
    import httpx

    url = base_url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url

    params: dict[str, str] = {"$format": "json"}
    if odata_filter.strip():
        params["$filter"] = odata_filter.strip()
    if select.strip():
        params["$select"] = select.strip()
    cap = min(max_rows or MAX_ROWS, MAX_ROWS)
    params["$top"] = str(min(top, cap) if top else cap)

    headers = {"Accept": "application/json"}
    auth = None
    if auth_type == "bearer" and secret:
        headers["Authorization"] = f"Bearer {secret}"
    elif username or secret:
        auth = httpx.BasicAuth(username, secret)

    collected: list[dict] = []
    next_url: str | None = url
    use_params: dict | None = params
    pages = 0
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        while next_url and len(collected) < cap and pages < MAX_PAGES:
            resp = client.get(next_url, params=use_params, headers=headers, auth=auth)
            resp.raise_for_status()
            rows, nxt = _rows_from_payload(resp.json())
            collected.extend(rows)
            pages += 1
            next_url, use_params = (nxt, None) if nxt else (None, None)  # nextLink ya trae el query

    collected = collected[:cap]
    flat = [_flatten(r) for r in collected if isinstance(r, dict)]
    cols: list[str] = []
    for r in flat:
        for k in r:
            if k not in cols:
                cols.append(k)
    data = [tuple(r.get(c, "") for c in cols) for r in flat]
    return cols, data
