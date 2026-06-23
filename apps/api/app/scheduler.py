"""In-process scheduler for time-based automations (APScheduler).

Gated by SCHEDULER_ENABLED. On serverless/managed hosts you can instead call
POST /automations/run-due from an external cron (or n8n) — same engine.
"""
from __future__ import annotations

from .config import settings

_scheduler = None


def _run_all(frequency: str) -> None:  # pragma: no cover - background job
    from sqlmodel import Session, select

    from .db import engine
    from .models import Tenant
    from .routers.automations import run_due

    with Session(engine) as session:
        for tenant in session.exec(select(Tenant)).all():
            try:
                run_due(session, tenant, frequency)
            except Exception:
                continue


def start() -> None:  # pragma: no cover - requires apscheduler + runtime
    global _scheduler
    if not settings.scheduler_enabled or _scheduler is not None:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except Exception:
        return  # apscheduler not installed -> no-op (use /automations/run-due)

    _scheduler = BackgroundScheduler(timezone="America/Mexico_City")
    _scheduler.add_job(lambda: _run_all("daily"), CronTrigger(hour=8, minute=0), id="daily")
    _scheduler.add_job(lambda: _run_all("weekly"), CronTrigger(day_of_week="mon", hour=8, minute=0), id="weekly")
    _scheduler.add_job(lambda: _run_all("monthly"), CronTrigger(day=1, hour=8, minute=0), id="monthly")
    _scheduler.start()
