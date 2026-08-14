"""Factory vector store — InMemory (dev) atau PGVector (prod)."""
from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_postgres import PGVector

from app.core.config import settings


def build_vector_store(embeddings: Embeddings):
    if settings.database_url.startswith("postgres"):
        return PGVector(
            embeddings=embeddings,
            connection=settings.database_url,
            collection_name="vendor_documents",
        )
    return InMemoryVectorStore(embeddings)