"""Factory checkpointer LangGraph — InMemory untuk dev/test, Postgres untuk prod."""
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import settings


def get_checkpointer():
    if settings.database_url.startswith("postgres"):
        from langgraph.checkpoint.postgres import PostgresSaver

        from sqlalchemy import create_engine

        engine = create_engine(settings.database_url)
        return PostgresSaver(engine)  # type: ignore[arg-type]
    return InMemorySaver()