"""Retriever aturan vendor dari vector store."""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.vectorstores import InMemoryVectorStore

from app.rag.store import build_vector_store


class VendorRetriever:
    def __init__(self, store):
        self._store = store

    def retrieve(self, vendor_id: str, sku: str, k: int = 4) -> list[str]:
        query = f"aturan pengadaan vendor {vendor_id} sku {sku} moq lead time diskon"
        results = self._store.similarity_search(query, k=k)
        return [doc.page_content for doc in results]

    @staticmethod
    def build_store_for_test(docs: list[Document]):
        store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
        store.add_documents(docs)
        return store