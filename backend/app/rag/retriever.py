"""Retriever aturan vendor dari vector store dengan filter metadata vendor."""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.vectorstores import InMemoryVectorStore

from app.rag.store import build_vector_store


class VendorRetriever:
    def __init__(self, store):
        self._store = store

    def _build_filter(self, vendor_id: str) -> dict:
        # InMemoryVectorStore menerima filter berupa callable, PGVector menerima dict.
        if isinstance(self._store, InMemoryVectorStore):
            return {"filter": lambda doc: doc.metadata.get("vendor_id") == vendor_id}
        return {"filter": {"vendor_id": vendor_id}}

    def _queries_for(self, vendor_id: str, sku: str) -> list[str]:
        # Multi-query per fakta: union hasilnya menaikkan recall section
        # yang kosakatanya tidak termuat di template query tunggal.
        return [
            f"aturan pengadaan vendor {vendor_id} sku {sku} moq lead time diskon",
            f"minimum order quantity MOQ khusus SKU {sku} vendor {vendor_id}",
            f"lead time pengiriman SKU {sku} vendor {vendor_id}",
            f"diskon volume dan klausul penalti SKU {sku} vendor {vendor_id}",
            f"ketentuan khusus per SKU {sku} vendor {vendor_id}",
        ]

    @staticmethod
    def _dedupe(docs: list[Document]) -> list[Document]:
        seen: set[str] = set()
        out: list[Document] = []
        for doc in docs:
            key = doc.id or doc.page_content
            if key in seen:
                continue
            seen.add(key)
            out.append(doc)
        return out

    def retrieve(self, vendor_id: str, sku: str, k: int = 8) -> list[Document]:
        filter_kwargs = self._build_filter(vendor_id)
        per_query = max(k // 3, 3)
        results: list[Document] = []
        for query in self._queries_for(vendor_id, sku):
            results.extend(self._store.similarity_search(query, k=per_query, **filter_kwargs))
        results = self._dedupe(results)[:k]
        if not results:
            # Fallback: bila tidak ada dokumen dengan vendor_id tersebut
            # (mis. korpus baru belum di-ingest), ambil tanpa filter.
            for query in self._queries_for(vendor_id, sku):
                results.extend(self._store.similarity_search(query, k=per_query))
            results = self._dedupe(results)[:k]
        return results

    @staticmethod
    def build_store_for_test(docs: list[Document]):
        store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
        store.add_documents(docs)
        return store