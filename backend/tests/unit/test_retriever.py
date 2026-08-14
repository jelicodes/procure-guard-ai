from app.rag.loader import load_documents
from app.rag.retriever import VendorRetriever
from langchain_core.embeddings import DeterministicFakeEmbedding


def test_retriever_finds_vendor_documents(tmp_path):
    doc_dir = tmp_path / "sops"
    doc_dir.mkdir()
    (doc_dir / "vendor-a.md").write_text(
        "MOQ 100 unit. Lead time 7 hari. Diskon 5% untuk 500 unit. Vendor A."
    )
    (doc_dir / "vendor-b.md").write_text(
        "MOQ 250 unit. Lead time 10 hari. Vendor B."
    )

    docs = load_documents(str(doc_dir))
    assert len(docs) == 2

    store = VendorRetriever.build_store_for_test(docs)
    retriever = VendorRetriever(store)
    # DeterministicFakeEmbedding mencari berdasarkan hash, bukan semantik,
    # jadi peringkat top-k tidak bisa diprediksi secara bermakna.
    # Verifikasi konten kedua SOP ter-retrieve (tidak bergantung urutan).
    hits = retriever.retrieve("VENDOR-A", "SKU-001", k=2)
    assert len(hits) == 2
    contents = " ".join(hits)
    assert "100" in contents
    assert "250" in contents
