"""Tes context-prepend: metadata section di-prepend ke konten chunk sebelum embedding."""
from app.rag.loader import load_documents


def test_loader_prepend_section_ke_page_content(tmp_path):
    doc_dir = tmp_path / "sops"
    (doc_dir / "vendor-c").mkdir(parents=True)
    (doc_dir / "vendor-c" / "sop.md").write_text(
        "# Perjanjian Vendor-C\n\n## 6. Ketentuan Khusus per SKU\n\nSKU-005 MOQ khusus 20.\n",
        encoding="utf-8",
    )

    docs = load_documents(str(doc_dir))

    assert len(docs) == 1
    content = docs[0].page_content
    assert "Ketentuan Khusus" in content, "section path harus di-prepend"
    assert "SKU-005" in content


def test_loader_prepend_tidak_menghilangkan_konten_asli(tmp_path):
    doc_dir = tmp_path / "sops"
    (doc_dir / "vendor-a").mkdir(parents=True)
    (doc_dir / "vendor-a" / "sop.md").write_text(
        "# Perjanjian Vendor-A\n\n## MOQ\n\nMOQ 100 unit.\n", encoding="utf-8"
    )

    docs = load_documents(str(doc_dir))

    assert "MOQ 100 unit." in docs[0].page_content
    assert docs[0].metadata["doc_id"] == "vendor-a/sop.md:Perjanjian Vendor-A > MOQ"
