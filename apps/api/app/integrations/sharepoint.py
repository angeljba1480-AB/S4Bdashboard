"""Lector de SharePoint (solo lectura) vía Microsoft Graph (token delegado).

Resuelve un sitio por su URL, lista los archivos de una carpeta del drive y los
descarga para importarlos al repositorio + RAG. No escribe nada en SharePoint.
"""
from __future__ import annotations

from urllib.parse import urlparse

GRAPH = "https://graph.microsoft.com/v1.0"
TIMEOUT = 30


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _site_id(client, token: str, site_url: str) -> str:
    u = urlparse(site_url.strip())
    host, path = u.netloc, u.path.rstrip("/")
    if not host:
        raise ValueError("URL de sitio inválida (usa https://host/sites/Nombre)")
    r = client.get(f"{GRAPH}/sites/{host}:{path}", headers=_auth(token), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["id"]


def _children_url(site_id: str, folder: str) -> str:
    folder = (folder or "").strip().strip("/")
    if folder:
        return f"{GRAPH}/sites/{site_id}/drive/root:/{folder}:/children"
    return f"{GRAPH}/sites/{site_id}/drive/root/children"


def list_files(token: str, site_url: str, folder: str = "") -> list[dict]:
    import httpx
    with httpx.Client() as client:
        site_id = _site_id(client, token, site_url)
        r = client.get(_children_url(site_id, folder), headers=_auth(token), timeout=TIMEOUT)
        r.raise_for_status()
        out = []
        for it in r.json().get("value", []):
            out.append({"id": it.get("id"), "name": it.get("name"),
                        "is_folder": "folder" in it, "size": it.get("size", 0),
                        "download": it.get("@microsoft.graph.downloadUrl", "")})
        return out


def fetch(token: str, site_url: str, folder: str = "", max_files: int = 50) -> list[tuple[str, bytes]]:
    """Descarga los archivos (no carpetas) de la carpeta indicada → [(nombre, bytes)]."""
    import httpx
    files = [f for f in list_files(token, site_url, folder) if not f["is_folder"] and f.get("download")]
    out: list[tuple[str, bytes]] = []
    with httpx.Client(follow_redirects=True) as client:
        for f in files[:max_files]:
            try:
                r = client.get(f["download"], timeout=TIMEOUT)
                r.raise_for_status()
                out.append((f["name"], r.content))
            except Exception:
                continue
    return out
