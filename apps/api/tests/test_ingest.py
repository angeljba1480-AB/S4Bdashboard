"""Ingesta documental: extracción de texto de PDF / DOCX / texto plano."""
from __future__ import annotations

import io
import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.ingest import extract_text  # noqa: E402


def _make_pdf(text: str) -> bytes:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import LETTER
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    c.drawString(72, 720, text)
    c.showPage()
    c.save()
    return buf.getvalue()


def _make_docx(text: str) -> bytes:
    from docx import Document as Docx
    d = Docx()
    d.add_paragraph(text)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_extract_pdf():
    pdf = _make_pdf("Propuesta comercial para ACME con alcance y precios.")
    out = extract_text(pdf, "propuesta.pdf", "application/pdf")
    assert "ACME" in out and "Propuesta" in out


def test_extract_docx():
    dx = _make_docx("Reglamento interno de trabajo — RH.")
    out = extract_text(dx, "reglamento.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert "Reglamento" in out and "RH" in out


def test_extract_plain_text_fallback():
    out = extract_text(b"hola mundo, csv,1,2,3", "datos.csv", "text/csv")
    assert "hola mundo" in out


def test_extract_xlsx():
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Cliente", "Venta"]); ws.append(["IMSS", 1000])
    buf = io.BytesIO(); wb.save(buf)
    out = extract_text(buf.getvalue(), "datos.xlsx")
    assert "Cliente" in out and "IMSS" in out and "1000" in out


def test_extract_zip_expands_inner_files():
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.txt", "contenido alpha")
        z.writestr("b.csv", "x,y\n1,2")
    out = extract_text(buf.getvalue(), "paquete.zip")
    assert "alpha" in out and "a.txt" in out and "b.csv" in out


def test_unknown_binary_returns_empty_not_garbage():
    blob = bytes([0, 1, 2, 3, 255, 254]) + b"\x00basura"
    assert extract_text(blob, "raro.bin", "application/octet-stream") == ""


def test_upload_pdf_indexes_text(client):
    h = _auth(client)
    pdf = _make_pdf("Contenido extraido de un PDF de prueba para el RAG.")
    r = client.post("/documents/upload", headers=h,
                    files={"file": ("prueba.pdf", pdf, "application/pdf")},
                    data={"area": "Ventas"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "prueba.pdf" and body["indexed"] is True
    # Aparece en el repositorio.
    docs = client.get("/documents", headers=h).json()
    assert any(d["filename"] == "prueba.pdf" for d in docs)
