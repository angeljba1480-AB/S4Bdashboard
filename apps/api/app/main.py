"""FastAPI application entrypoint for the Private AI Platform."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .routers import (
    admin,
    agents,
    audit,
    auth_routes,
    chat,
    documents,
    usage,
    workflows,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from .seed import seed

    seed()
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(agents.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(workflows.router)
app.include_router(audit.router)
app.include_router(usage.router)
app.include_router(admin.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "private-ai-platform-api", "env": settings.app_env}
