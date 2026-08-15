"""Test factory checkpointer — branch prod (Postgres) dapat diimpor tanpa error."""
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver


def test_prod_checkpointer_postgres_import_dan_bangun():
    # Tanpa Postgres live di mesin: cukup pastikan dependency terinstal dan
    # objek PostgresSaver dapat dibangun (tanpa koneksi DB di konstruktor).
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool("postgresql://procure:procure@localhost:5432/procure", open=False)
    saver = PostgresSaver(pool)
    assert isinstance(saver, PostgresSaver)


def test_dev_checkpointer_tetap_inmemory():
    # Path dev/test memakai InMemorySaver (tanpa setup DB) — tidak boleh berubah.
    from app.core.checkpointer import get_checkpointer
    from app.core.config import settings

    assert settings.database_url.startswith("sqlite")
    checkpointer = get_checkpointer()
    assert isinstance(checkpointer, InMemorySaver)