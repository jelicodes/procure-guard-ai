"""Service ingest dokumen SOP vendor ke vector store."""
from __future__ import annotations

import logging

from langchain_core.documents import Document

from app.core.llm import get_embeddings
from app.rag.loader import load_documents
from app.rag.store import build_vector_store

logger = logging.getLogger(__name__)


def ingest_sops(directory: str) -> int:
    docs = load_documents(directory)
    store = build_vector_store(get_embeddings())
    store.add_documents(docs)
    logger.info("Berhasil meng-ingest %d dokumen SOP dari %s", len(docs), directory)
    return len(docs)