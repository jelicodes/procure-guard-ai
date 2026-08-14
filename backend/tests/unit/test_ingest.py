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