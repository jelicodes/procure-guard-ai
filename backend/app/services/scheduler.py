"""Scheduler berkala untuk scan low-stock (APScheduler in-process)."""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler(interval_minutes: int = 60, runnable=None, deps=None) -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="Asia/Jakarta")

    if runnable is None:
        from app.agents.deps import build_default_deps
        from app.rag.retriever import VendorRetriever
        from app.core.llm import get_embeddings
        from app.rag.store import build_vector_store

        store = build_vector_store(get_embeddings())
        retriever = VendorRetriever(store)
        built_deps = asyncio.run(build_default_deps(retriever))
        deps = deps or built_deps

        async def _job():
            from app.agents.graph import run_scan

            try:
                out = await run_scan(deps)
                if out["po"]:
                    logger.info("Scan %s -> PO %s status=%s", out["thread_id"], out["po"].po_no, out["po"].status)
            except Exception:
                logger.exception("Scan terjadwal gagal")

        runnable = lambda: asyncio.run(_job())  # noqa: E731

    _scheduler.add_job(runnable, "interval", minutes=interval_minutes, id="inventory_scan", replace_existing=True)
    _scheduler.start()
    logger.info("Scheduler dimulai, interval=%s menit", interval_minutes)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
