"""Conocimiento de la plataforma + reglas anti-alucinación en el system prompt."""
from __future__ import annotations

from app.ai.platform_kb import build_system


def test_build_system_includes_rules_and_capabilities():
    s = build_system("Eres el agente de Ventas.")
    # Reglas de formato (texto plano) y anti-alucinación.
    assert "TEXTO PLANO" in s and "```" in s
    assert "Anti-alucinación" in s and "No tengo esa información" in s
    # Capacidades para responder "¿en qué me ayuda la plataforma?".
    assert "CAPACIDADES DE LA PLATAFORMA" in s
    assert "RAG" in s and "Agente de acciones" in s
    # Incluye el rol del agente.
    assert "agente de Ventas" in s


def test_build_system_without_agent_prompt():
    s = build_system("")
    assert "CAPACIDADES DE LA PLATAFORMA" in s and "Rol del agente" not in s
