"""Acceso al dataset del Tablero Financiero.

Todos los datos vienen **inyectados** (ver ``dataset.py``): primero lo que el cliente
sube en la app (``store.py``, por tenant, cifrado), luego variable/secret de entorno y,
como último recurso, un ``demo_dataset.json`` sintético. El repositorio no guarda datos
reales del cliente.

``Dataset`` envuelve un dict y expone los accesores; ``for_tenant`` resuelve el dataset
del tenant (BD → entorno → demo). Las constantes de módulo se mantienen por
compatibilidad (apuntan al dataset global/demo).
"""
from __future__ import annotations

from . import dataset


class Dataset:
    """Accesor sobre un dict de dataset (mismo contrato en demo, entorno o subido)."""

    def __init__(self, data: dict):
        self.d = data

    @property
    def company(self) -> dict: return self.d.get("company", {})
    @property
    def headcount(self) -> dict: return self.d.get("headcount", {})
    @property
    def fy(self) -> dict: return self.d.get("fy", {})
    @property
    def fy_2024(self) -> dict: return self.d.get("fy_2024", {})
    @property
    def monthly(self) -> dict: return self.d.get("monthly", {})
    @property
    def segments(self) -> dict: return self.d.get("segments", {})
    @property
    def gob_ip(self) -> dict: return self.d.get("gob_ip", {})
    @property
    def benchmarks(self) -> list: return self.d.get("benchmarks", [])
    @property
    def alerts(self) -> list: return self.d.get("alerts", [])
    @property
    def top_clients(self) -> list: return self.d.get("top_clients", [])

    def projects(self) -> dict: return self.d.get("projects", {})
    def utilization(self) -> dict: return self.d.get("utilization", {})
    def cost_per_hour(self) -> dict: return self.d.get("cost_per_hour", {})
    def client_scoring(self) -> dict: return self.d.get("client_scoring", {})
    def cost_comparison(self) -> dict: return self.d.get("cost_comparison", {})
    def is_demo(self) -> bool: return bool(self.d.get("_is_demo"))
    def origin(self) -> str: return self.d.get("_origin", "")

    def entity_kpis(self, entity: str) -> dict:
        fy = self.fy
        d = fy.get(entity, fy.get("CONS", {}))
        prev = self.fy_2024.get(entity, self.fy_2024.get("CONS", {}))
        growth = (d["revenue"] / prev["revenue"] - 1) if prev.get("revenue") else 0.0
        return {**d, "growth": growth}


def global_dataset() -> Dataset:
    return Dataset(dataset.load())


def for_tenant(session, tenant) -> Dataset:
    """Dataset del tenant si subió uno; si no, el global (entorno/demo)."""
    from . import store
    data = store.get_dataset(session, tenant) if (session is not None and tenant is not None) else None
    return Dataset(data) if data else global_dataset()


# --- Compatibilidad: constantes/accesores a nivel módulo (dataset global/demo) ---
_D = dataset.load()
COMPANY = _D["company"]
HEADCOUNT = _D["headcount"]
FY = _D["fy"]
FY_2024 = _D["fy_2024"]
MONTHLY = _D["monthly"]
SEGMENTS = _D["segments"]
GOB_IP = _D["gob_ip"]
BENCHMARKS = _D["benchmarks"]
ALERTS = _D["alerts"]
TOP_CLIENTS = _D["top_clients"]


def projects() -> dict: return dataset.load().get("projects", {})
def utilization() -> dict: return dataset.load().get("utilization", {})
def cost_per_hour() -> dict: return dataset.load().get("cost_per_hour", {})
def client_scoring() -> dict: return dataset.load().get("client_scoring", {})
def cost_comparison() -> dict: return dataset.load().get("cost_comparison", {})
def is_demo() -> bool: return dataset.is_demo()


def entity_kpis(entity: str) -> dict:
    return global_dataset().entity_kpis(entity)
