"""Service ingest dokumen SOP vendor ke vector store (idempoten)."""
from __future__ import annotations

import logging

from app.core.llm import get_embeddings
from app.rag.loader import load_documents
from app.rag.store import build_vector_store

logger = logging.getLogger(__name__)


def ingest_sops(directory: str) -> int:
    docs = load_documents(directory)
    if not docs:
        logger.info("Tidak ada dokumen SOP di %s", directory)
        return 0
    store = build_vector_store(get_embeddings())
    ids = [doc.id for doc in docs if doc.id]
    # Idempoten: hapus versi dokumen yang sama (berdasarkan doc_id) sebelum menambah ulang,
    # agar re-ingest tidak menduplikasi chunk di PGVector (dev InMemory selalu baru).
    try:
        store.delete(ids=ids)
    except Exception:
        logger.warning("Gagal membersihkan dokumen lama sebelum ingest (diabaikan)")
    store.add_documents(docs)
    logger.info("Berhasil meng-ingest %d dokumen SOP dari %s", len(docs), directory)
    return len(docs)