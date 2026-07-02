"""P0 de seguridad: la compuerta de arranque en producción y el gate del seed demo.

Prueba comportamiento real (no mocks): construye Settings con distintos entornos y
verifica que (a) el secreto por defecto bloquea en producción, (b) un secreto propio
pasa, y (c) el seed demo no siembra credenciales conocidas en producción salvo opt-in.
"""
from __future__ import annotations

import os
import tempfile

from app.config import Settings

_STRONG = "x" * 48  # secreto propio de >=32 chars


def test_secret_por_defecto_bloquea_en_produccion():
    s = Settings(app_env="production")  # secret_key = default
    errs = s.security_errors()
    assert errs and any("SECRET_KEY" in e for e in errs)


def test_secreto_propio_pasa_en_produccion():
    s = Settings(app_env="production", secret_key=_STRONG, master_kms_key=_STRONG)
    assert s.security_errors() == []


def test_dev_no_exige_secreto():
    # En desarrollo no bloqueamos (el default es aceptable para correr local/tests).
    s = Settings(app_env="development")
    assert s.is_production is False


def test_seed_demo_gate():
    # dev: siembra; prod sin opt-in: NO; prod con opt-in explícito: sí.
    assert Settings(app_env="development").should_seed_demo is True
    assert Settings(app_env="production", secret_key=_STRONG, master_kms_key=_STRONG).should_seed_demo is False
    assert Settings(app_env="production", secret_key=_STRONG, master_kms_key=_STRONG,
                    seed_demo_data=True).should_seed_demo is True


def test_cors_solo_permite_maestroai_no_vercel_ni_lookalikes():
    import re
    s = Settings()
    rx = re.compile(s.cors_origin_regex)
    def allowed(o: str) -> bool:
        return bool(rx.fullmatch(o))
    # Permitidos: el portal y subdominios de maestroai.mx
    assert allowed("https://plataforma.maestroai.mx")
    assert allowed("https://maestroai.mx")
    # Rechazados: cualquier *.vercel.app (el agujero P0) y lookalikes
    assert not allowed("https://evil.vercel.app")
    assert not allowed("https://maestroai.mx.attacker.com")
    assert not allowed("https://evilmaestroai.mx")
    assert "vercel.app" not in s.cors_origin_regex
    assert "https://plataforma.maestroai.mx" in s.cors_origin_list


def test_seed_no_toca_bd_en_produccion(monkeypatch):
    """Con APP_ENV=production y sin opt-in, seed() corta ANTES de abrir la BD:
    si intentara sembrar, la sesión-centinela lanzaría."""
    import app.config as cfg
    import app.seed as seedmod

    prod = Settings(app_env="production", secret_key=_STRONG, master_kms_key=_STRONG)
    monkeypatch.setattr(cfg, "settings", prod)

    def _boom(*a, **k):
        raise AssertionError("seed() abrió una sesión de BD en producción — no debía sembrar")

    monkeypatch.setattr(seedmod, "Session", _boom)
    seedmod.seed()  # no debe lanzar: corta por el gate should_seed_demo


def test_seed_si_siembra_con_optin_en_produccion(monkeypatch):
    """Con opt-in explícito (SEED_DEMO_DATA=true) sí intenta sembrar (abre sesión)."""
    import app.config as cfg
    import app.seed as seedmod

    prod = Settings(app_env="production", secret_key=_STRONG, master_kms_key=_STRONG,
                    seed_demo_data=True)
    monkeypatch.setattr(cfg, "settings", prod)

    opened = {"v": False}

    class _Sentinel:
        def __init__(self, *a, **k):
            opened["v"] = True
            raise RuntimeError("stop")  # cortamos aquí; solo verificamos que abrió sesión

    monkeypatch.setattr(seedmod, "Session", _Sentinel)
    try:
        seedmod.seed()
    except RuntimeError:
        pass
    assert opened["v"] is True
