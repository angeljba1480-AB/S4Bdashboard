"""FastAPI application entrypoint for the Private AI Platform."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .routers import (
    actions,
    admin,
    agents,
    apps,
    automations,
    audit,
    auth_routes,
    chat,
    company,
    dashboards,
    datasources,
    documents,
    drive,
    export,
    finetune,
    flowcharts,
    images,
    memory,
    notebooks,
    integrations,
    oauth,
    alerts,
    recipes,
    regional,
    runbooks,
    search,
    sso,
    voice,
    tramites,
    usage,
    v1,
    workflows,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from .seed import ensure_super_admin, seed

    seed()
    ensure_super_admin()
    # Load admin-configured external providers into the adapter runtime cache.
    from .ai.adapters import load_overrides
    from .db import get_session as _gs
    from . import runtime_config
    _s = next(_gs())
    try:
        load_overrides(_s)
        runtime_config.load(_s)
    finally:
        _s.close()
    if settings.scheduler_enabled:
        from .scheduler import start as start_scheduler
        start_scheduler()
    yield


app = FastAPI(
    title="Private AI Platform — API",
    description="Private AI Gateway + Vertical Agents. Router de privacidad, RAG seguro y auditoría.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Also accept any Vercel deployment (production + preview URLs) so the portal
    # connects without having to enumerate every preview domain. Configurable via
    # CORS_ORIGIN_REGEX; defaults to *.vercel.app.
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(sso.router)
app.include_router(agents.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(recipes.router)
app.include_router(regional.router)
app.include_router(tramites.router)
app.include_router(dashboards.router)
app.include_router(apps.router)
app.include_router(automations.router)
app.include_router(integrations.router)
app.include_router(oauth.router)
app.include_router(v1.router)
app.include_router(workflows.router)
app.include_router(audit.router)
app.include_router(usage.router)
app.include_router(admin.router)
app.include_router(company.router)
app.include_router(export.router)
app.include_router(flowcharts.router)
app.include_router(drive.router)
app.include_router(notebooks.router)
app.include_router(actions.router)
app.include_router(memory.router)
app.include_router(datasources.router)
app.include_router(images.router)
app.include_router(finetune.router)
app.include_router(voice.router)
app.include_router(alerts.router)
app.include_router(search.router)
app.include_router(runbooks.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "private-ai-platform-api", "env": settings.app_env}
