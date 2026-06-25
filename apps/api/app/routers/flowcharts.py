"""/flowcharts — navigable base flows (blueprint §3) + the generic use-case flow."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import flowcharts as catalog
from ..auth import get_current_user
from ..models import User

router = APIRouter(prefix="/flowcharts", tags=["flowcharts"])


@router.get("")
def list_flowcharts(_: User = Depends(get_current_user)) -> list[dict]:
    return catalog.list_flowcharts()


@router.get("/{flow_id}")
def get_flowchart(flow_id: str, _: User = Depends(get_current_user)) -> dict:
    flow = catalog.get_flowchart(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flujograma no encontrado")
    return flow
