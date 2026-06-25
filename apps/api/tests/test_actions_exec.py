"""Ejecución del toolkit (Microsoft Graph): construcción de URL/cuerpo y escapado
OData de los nuevos verbos Excel/SharePoint. Se mockea httpx — sin red real."""
from __future__ import annotations

import httpx
import pytest

from app.integrations import actions_exec


class _Resp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_odata_literal_escapes_single_quotes():
    assert actions_exec._odata_literal("O'Brien") == "O''Brien"
    assert actions_exec._odata_literal(None) == ""


def test_excel_read_builds_workbook_range_url(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return _Resp({"values": [["a", "b"], ["1", "2"]]})

    monkeypatch.setattr(httpx, "get", fake_get)
    out = actions_exec.execute("excel.read", "tok", {
        "item_id": "01ABC", "worksheet": "Hoja's", "range": "A1:B2"})
    assert "workbook/worksheets('Hoja''s')" in captured["url"]  # comilla escapada
    assert "range(address='A1:B2')" in captured["url"]
    assert "a | b" in out and "1 | 2" in out


def test_sharepoint_search_posts_query_in_body(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return _Resp({"value": [{"hitsContainers": [
            {"hits": [{"resource": {"name": "Propuesta.docx"}}]}]}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    out = actions_exec.execute("sharepoint.search", "tok", {"query": "propuesta ISO"})
    assert captured["url"].endswith("/search/query")
    # El término va en el cuerpo JSON (httpx lo escapa) — no en la URL.
    assert captured["json"]["requests"][0]["query"]["queryString"] == "propuesta ISO"
    assert "Propuesta.docx" in out


def test_sharepoint_search_empty_query_short_circuits(monkeypatch):
    def boom(*a, **k):  # no debe llamar a la red
        raise AssertionError("no debería invocar httpx")

    monkeypatch.setattr(httpx, "post", boom)
    assert "término" in actions_exec.execute("sharepoint.search", "tok", {"query": "  "})


def test_excel_append_builds_table_add_url(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return _Resp({})

    monkeypatch.setattr(httpx, "post", fake_post)
    out = actions_exec.execute("excel.append", "tok", {
        "item_id": "01ABC", "table": "Ventas", "values": "ACME, 5000"})
    assert "workbook/tables('Ventas')/rows/add" in captured["url"]
    assert captured["json"]["values"] == [["ACME", "5000"]]
    assert "Ventas" in out


def test_unknown_action_raises():
    with pytest.raises(ValueError):
        actions_exec.execute("nope.x", "tok", {})
