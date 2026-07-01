#!/usr/bin/env python3
"""Genera el bundle que consume el reporte standalone (apps/report) a partir de los
endpoints del Tablero Financiero de la API.

Uso:
    # Bundle DEMO (fallback versionado, datos de ejemplo):
    python apps/report/scripts/build_bundle.py --demo -o apps/report/src/data/demo_bundle.json

    # Bundle REAL desde archivos del cliente (NO se commitea; va a la env var REPORT_DATA):
    python apps/report/scripts/build_bundle.py \
        --files nomina.xlsx timesheet.xlsx "Proyectos Finanzas.zip" evaluacion.xlsx \
        --mark-demo resumen finanzas posicion clientes benchmark alertas \
        -o real_bundle.json

Luego, en Vercel, configura REPORT_DATA con el contenido de real_bundle.json (o su
base64). El repositorio nunca contiene las cifras reales.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

# Permite ejecutar desde la raíz del repo apuntando a la API.
API_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "api")
sys.path.insert(0, os.path.abspath(API_DIR))


def _capture(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    ents = ["S4B", "S4C", "CONS"]
    return {
        "overview": {e: client.get(f"/finance/overview?entity={e}", headers=h).json() for e in ents},
        "clients": {e: client.get(f"/finance/clients?entity={e}", headers=h).json() for e in ents},
        "projects": client.get("/finance/projects", headers=h).json(),
        "operations": client.get("/finance/operations", headers=h).json(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="usa el demo_dataset.json del repo")
    ap.add_argument("--files", nargs="*", default=[], help="Excel/zip/json del cliente")
    ap.add_argument("--mark-demo", nargs="*", default=[], help="vistas a etiquetar como demo")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    fd, dbpath = tempfile.mkstemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite:///{dbpath}"

    if args.demo:
        with open(os.path.join(API_DIR, "app", "finance", "demo_dataset.json")) as f:
            os.environ["FINANCE_DATASET_JSON"] = f.read()
    elif args.files:
        from app.finance.ingest_excel import build_dataset_from_files
        payload = []
        for p in args.files:
            with open(p, "rb") as f:
                payload.append((os.path.basename(p), f.read()))
        data = build_dataset_from_files(payload)
        data.pop("_source_files", None)
        os.environ["FINANCE_DATASET_JSON"] = json.dumps(data, ensure_ascii=False)

    # build_dataset_from_files ya llamó a dataset.load() (lru_cache) con la fuente previa;
    # hay que invalidar la caché para que la API sirva el JSON que acabamos de inyectar.
    from app.finance import dataset as _ds
    _ds.load.cache_clear()

    from fastapi.testclient import TestClient
    from app.main import app

    _ds.load.cache_clear()
    with TestClient(app) as c:
        bundle = _capture(c)

    if args.demo:
        for e in bundle["overview"].values():
            e["is_demo"] = True
            e["source"] = "demo (datos de ejemplo)"
        bundle["operations"]["is_demo"] = True
    if args.mark_demo:
        bundle["demoSections"] = args.mark_demo

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False)
    print(f"escrito {args.out} · demoSections={bundle.get('demoSections') or ('todo' if args.demo else 'ninguno')}")


if __name__ == "__main__":
    main()
