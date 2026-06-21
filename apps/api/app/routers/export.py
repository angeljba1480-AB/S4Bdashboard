"""Export endpoints (blueprint backlog: "Export reports" — DOCX/PDF).

Generates PDF or Markdown from a conversation transcript or arbitrary report
content (SOWs, cyber diagnostics, executive summaries).
"""
from __future__ import annotations

import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import AuditEvent, Conversation, Message, Tenant, User

router = APIRouter(prefix="/export", tags=["export"])


class ReportRequest(BaseModel):
    title: str
    content: str
    format: str = "pdf"  # pdf | md


def _render_pdf(title: str, blocks: list[tuple[str, str]]) -> bytes:
    """blocks = list of (heading, body). Pure-Python via reportlab."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, title=title)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]),
             Paragraph(f"Generado {datetime.utcnow():%Y-%m-%d %H:%M} UTC · Private AI Platform",
                       styles["Italic"]),
             Spacer(1, 16)]
    for heading, body in blocks:
        if heading:
            story.append(Paragraph(heading, styles["Heading3"]))
        for line in (body or "").split("\n"):
            story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;") or "&nbsp;", styles["BodyText"]))
        story.append(Spacer(1, 10))
    doc.build(story)
    return buf.getvalue()


def _render_md(title: str, blocks: list[tuple[str, str]]) -> str:
    out = [f"# {title}", f"_Generado {datetime.utcnow():%Y-%m-%d %H:%M} UTC · Private AI Platform_", ""]
    for heading, body in blocks:
        if heading:
            out.append(f"## {heading}")
        out.append(body or "")
        out.append("")
    return "\n".join(out)


@router.post("/report")
def export_report(
    body: ReportRequest,
    _: User = Depends(get_current_user),
    __: Tenant = Depends(get_current_tenant),
):
    blocks = [("", body.content)]
    if body.format == "md":
        return Response(_render_md(body.title, blocks), media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="{body.title}.md"'})
    pdf = _render_pdf(body.title, blocks)
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{body.title}.pdf"'})


@router.get("/conversation/{conversation_id}")
def export_conversation(
    conversation_id: str,
    format: str = "pdf",
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    conv = session.get(Conversation, conversation_id)
    if not conv or conv.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    msgs = session.exec(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
    ).all()
    blocks = [
        (f"{'Usuario' if m.role == 'user' else 'Asistente'}"
         f"{f' · {m.model_used} ({m.route.value})' if m.role == 'assistant' else ''}",
         m.content_redacted)
        for m in msgs
    ]
    title = conv.title or "Conversación"
    if format == "md":
        return Response(_render_md(title, blocks), media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="{conv.id}.md"'})
    pdf = _render_pdf(title, blocks)
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{conv.id}.pdf"'})
