"""Planner agéntico: encadenamiento de pasos y validación de herramientas."""
from __future__ import annotations

from app.ai.agent_planner import _validate, plan_steps, resolve_refs

ACTIONS = [
    {"id": "gmail.send", "provider": "google", "label": "Enviar correo", "write": True, "params": ["to", "subject", "body"]},
    {"id": "sharepoint.search", "provider": "microsoft", "label": "Buscar SharePoint", "write": False, "params": ["query"]},
]
WORKFLOWS = [{"id": "ingesta", "name": "Ingesta documental", "steps": "Upload → ..."}]


def test_resolve_refs_chains_outputs():
    params = {"body": "Resumen: {{step1}}", "subject": "x"}
    out = resolve_refs(params, {1: "hola mundo"})
    assert out["body"] == "Resumen: hola mundo" and out["subject"] == "x"


def test_resolve_refs_keeps_unknown_ref():
    out = resolve_refs({"body": "{{step5}}"}, {1: "a"})
    assert out["body"] == "{{step5}}"


def test_validate_accepts_workflow_and_filters_params():
    steps = [
        {"action": "workflow:ingesta", "params": {"payload": "x", "ajeno": 1}, "reason": "r"},
        {"action": "gmail.send", "params": {"to": "a@b.com", "hack": "no"}},
        {"action": "no.existe", "params": {}},
    ]
    out = _validate(steps, ACTIONS, WORKFLOWS)
    assert [s["action"] for s in out] == ["workflow:ingesta", "gmail.send"]
    assert out[0]["params"] == {"payload": "x"}
    assert out[1]["params"] == {"to": "a@b.com"}


def test_plan_heuristic_matches_workflow_and_action():
    plan = plan_steps("haz la ingesta documental y busca en sharepoint", ACTIONS, workflows=WORKFLOWS)
    ids = {s["action"] for s in plan["steps"]}
    assert "workflow:ingesta" in ids and "sharepoint.search" in ids
    assert plan["source"] == "heurística"
