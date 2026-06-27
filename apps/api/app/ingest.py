"""Extracción de texto para la ingesta documental.

Soporta texto/CSV (decodificación directa), PDF (pypdf) y Word .docx (python-docx).
Para PDFs escaneados (sin capa de texto) intenta OCR si hay binario disponible
(pytesseract + pdf2image); si no, degrada de forma segura sin romper la carga.
"""
from __future__ import annotations

import io


def _pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception:  # pragma: no cover - dependencia ausente
        return ""
    try:
        reader = PdfReader(io.BytesIO(raw))
        parts = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(parts).strip()
    except Exception:
        text = ""
    # PDF escaneado (poca/ninguna capa de texto): intenta OCR opcional.
    if len(text) < 20:
        ocr = _ocr_pdf(raw)
        if ocr:
            return ocr
    return text


def _ocr_pdf(raw: bytes) -> str:
    """OCR opcional: solo si pytesseract + pdf2image + tesseract están instalados."""
    try:  # pragma: no cover - depende de binario del sistema
        import pytesseract
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(raw, dpi=200)
        return "\n".join(pytesseract.image_to_string(img, lang="spa+eng") for img in images).strip()
    except Exception:
        return ""


def _docx_text(raw: bytes) -> str:
    try:
        from docx import Document as Docx
    except Exception:  # pragma: no cover
        return ""
    try:
        d = Docx(io.BytesIO(raw))
        paras = [p.text for p in d.paragraphs if p.text]
        for table in d.tables:
            for row in table.rows:
                paras.append(" | ".join(c.text for c in row.cells))
        return "\n".join(paras).strip()
    except Exception:
        return ""


def extract_text(raw: bytes, filename: str = "", mime: str = "") -> str:
    """Devuelve el texto de un archivo subido según su tipo. Nunca lanza: si no
    puede extraer, cae a una decodificación de texto best-effort."""
    name = (filename or "").lower()
    mime = (mime or "").lower()

    # Para binarios (PDF/DOCX) NUNCA caemos a decodificar los bytes crudos: si no
    # se pudo extraer texto, devolvemos cadena vacía (mejor "sin texto" que basura).
    if name.endswith(".pdf") or "application/pdf" in mime:
        return _pdf_text(raw)
    if name.endswith(".docx") or "wordprocessingml" in mime:
        return _docx_text(raw)

    # Texto plano, CSV, Markdown, JSON…
    return raw.decode("utf-8", errors="ignore")
