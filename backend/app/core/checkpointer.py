"""Factory checkpointer LangGraph — InMemory untuk dev/test, Postgres untuk prod."""
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import settings


def get_checkpointer():
    if settings.database_url.startswith("postgres"):
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool

        # Normalisasi URL SQLAlchemy ("postgresql+psycopg://...") menjadi URL psycopg murni.
        url = settings.database_url.replace("+psycopg", "", 1)
        pool = ConnectionPool(url, open=False)
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()  # buat tabel checkpoint sekali sebelum ainvoke pertama
        return checkpointer
    return InMemorySaver()