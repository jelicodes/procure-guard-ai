"""Tes multi-query deterministik pada retriever (per fakta: MOQ/lead/diskon/khusus SKU)."""
from langchain_core.documents import Document

from app.rag.retriever import VendorRetriever


class RecordingStore:
    """Store palsu yang mencatat query dan filter, lalu mengembalikan dokumen tetap."""

    def __init__(self, docs: list[Document]):
        self._docs = docs
        self.queries: list[str] = []
        self.filters: list[dict] = []

    def similarity_search(self, query: str, k: int = 4, **kwargs):
        self.queries.append(query)
        self.filters.append(kwargs)
        return self._docs[:k]


def _docs():
    return [
        Document(
            page_content="MOQ umum 500. SKU-005 MOQ khusus 20.",
            metadata={"vendor_id": "VENDOR-C", "source": "vendor-c.md", "section": "MOQ", "doc_id": "va:moq"},
            id="va:moq",
        ),
        Document(
            page_content="Lead time umum 15. SKU-005 lead khusus 30.",
            metadata={"vendor_id": "VENDOR-C", "source": "vendor-c.md", "section": "Lead", "doc_id": "va:lead"},
            id="va:lead",
        ),
    ]


def test_retrieve_menjalankan_beberapa_query_per_fakta():
    store = RecordingStore(_docs())
    retriever = VendorRetriever(store)

    retriever.retrieve("VENDOR-C", "SKU-005", k=8)

    assert len(store.queries) >= 3, f"harus >1 query, dapat: {store.queries}"
    assert any("khusus" in q and "SKU" in q for q in store.queries), f"query ketentuan khusus hilang: {store.queries}"
    assert any("moq" in q.lower() for q in store.queries)
    assert any("lead" in q.lower() for q in store.queries)


def test_retrieve_semua_query_difilter_vendor_id():
    store = RecordingStore(_docs())
    retriever = VendorRetriever(store)

    retriever.retrieve("VENDOR-C", "SKU-005", k=8)

    for f in store.filters:
        callable_or_dict = list(f.values())[0]
        if callable(callable_or_dict):
            assert callable_or_dict(_docs()[0]) is True
            assert callable_or_dict(Document(metadata={"vendor_id": "VENDOR-X"})) is False
        else:
            assert callable_or_dict.get("vendor_id") == "VENDOR-C"


def test_retrieve_union_dedupe_by_doc_id():
    store = RecordingStore(_docs())
    retriever = VendorRetriever(store)

    hits = retriever.retrieve("VENDOR-C", "SKU-005", k=8)

    ids = [h.id for h in hits]
    assert ids == list(dict.fromkeys(ids)), f"ada duplikat doc_id: {ids}"
    assert len(hits) == len(_docs())
