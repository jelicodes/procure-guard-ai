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
    hits = retriever.retrieve("VENDOR-A", "SKU-001", k=2)
    assert len(hits) == 1
    assert "100" in hits[0].page_content


def test_retriever_filter_mencegah_kebocoran_antar_vendor(tmp_path):
    doc_dir = tmp_path / "sops"
    doc_dir.mkdir()
    (doc_dir / "vendor-a.md").write_text(
        "MOQ 100 unit. Lead time 7 hari. Vendor A."
    )
    (doc_dir / "vendor-b.md").write_text(
        "MOQ 250 unit. Lead time 10 hari. Vendor B."
    )

    docs = load_documents(str(doc_dir))
    store = VendorRetriever.build_store_for_test(docs)
    retriever = VendorRetriever(store)

    hits_a = retriever.retrieve("VENDOR-A", "SKU-001", k=4)
    assert all(d.metadata["vendor_id"] == "VENDOR-A" for d in hits_a)
    contents_a = " ".join(d.page_content for d in hits_a)
    assert "100" in contents_a
    assert "250" not in contents_a


def test_retriever_kembalikan_dokumen_dengan_metadata():
    from langchain_core.documents import Document

    doc = Document(
        page_content="MOQ 100 unit. Vendor A.",
        metadata={"vendor_id": "VENDOR-A", "source": "vendor-a.md", "section": "MOQ"},
    )
    store = VendorRetriever.build_store_for_test([doc])
    retriever = VendorRetriever(store)

    hits = retriever.retrieve("VENDOR-A", "SKU-001", k=1)
    assert hits[0].metadata["vendor_id"] == "VENDOR-A"
    assert hits[0].metadata["source"] == "vendor-a.md"


def test_retriever_fallback_ke_hasil_tanpa_filter_bila_vendor_tidak_ditemukan(tmp_path):
    """Saat korpus belum di-ingest untuk vendor tersebut, retriever tidak gagal total."""
    doc_dir = tmp_path / "sops"
    doc_dir.mkdir()
    (doc_dir / "vendor-a.md").write_text("MOQ 100 unit. Lead time 7 hari. Vendor A.")

    docs = load_documents(str(doc_dir))
    store = VendorRetriever.build_store_for_test(docs)
    retriever = VendorRetriever(store)

    hits = retriever.retrieve("VENDOR-Z", "SKU-999", k=2)
    assert hits  # fallback: masih mengembalikan hasil tanpa filter
    assert "100" in " ".join(d.page_content for d in hits)