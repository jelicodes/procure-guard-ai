"""Tes service ingest SOP vendor dan CLI (tanpa panggilan API nyata)."""
import pytest

from langchain_core.embeddings import DeterministicFakeEmbedding


@pytest.fixture
def fake_embeddings(monkeypatch):
    """Pakai embeddings deterministik agar tidak butuh Google API key."""
    from app.services import ingest

    monkeypatch.setattr(ingest, "get_embeddings", lambda: DeterministicFakeEmbedding(size=8))
    return ingest


def test_ingest_sops_memuat_dokumen_dan_mengembalikan_jumlah(tmp_path, fake_embeddings):
    doc_dir = tmp_path / "sops"
    doc_dir.mkdir()
    (doc_dir / "vendor-a.md").write_text(
        "MOQ 100 unit. Lead time 7 hari. Diskon 5% untuk 500 unit. Vendor A."
    )

    count = fake_embeddings.ingest_sops(str(doc_dir))

    assert count == 1


def test_ingest_sops_gagal_untuk_direktori_kosong(tmp_path, fake_embeddings):
    doc_dir = tmp_path / "sops"
    doc_dir.mkdir()

    count = fake_embeddings.ingest_sops(str(doc_dir))

    assert count == 0


def test_ingest_idempoten_tidak_menduplikasi_pada_store_yang_sama(tmp_path, monkeypatch):
    """Simulasi re-ingest pada store yang sama (kasus PGVector) tidak menduplikasi."""
    import app.services.ingest as ingest_mod
    from langchain_core.vectorstores import InMemoryVectorStore

    doc_dir = tmp_path / "sops"
    doc_dir.mkdir()
    (doc_dir / "vendor-a.md").write_text(
        "MOQ 100 unit. Lead time 7 hari. Vendor A."
    )

    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    docs = ingest_mod.load_documents(str(doc_dir))
    ids = [doc.id for doc in docs]

    # Pola yang dipakai ingest_sops: delete lalu add, dua kali.
    for _ in range(2):
        store.delete(ids=ids)
        store.add_documents(docs)

    assert len(store.store) == len(docs)