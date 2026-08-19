"""Tes loader dokumen SOP: struktur subfolder, doc_id, PDF, dan file datar."""
from app.rag.loader import load_documents


def _minimal_pdf_bytes(text: str) -> bytes:
    """Bangun PDF minimal yang valid (Helvetica, satu halaman)."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n".encode("latin-1") + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode("latin-1") + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )
    return bytes(out)


def test_loader_subfolder_menurunkan_vendor_id_dari_nama_folder(tmp_path):
    doc_dir = tmp_path / "sops"
    (doc_dir / "vendor-a").mkdir(parents=True)
    (doc_dir / "vendor-a" / "sop.md").write_text(
        "# Perjanjian Vendor-A\n\n## MOQ\n\nMOQ 100 unit.\n", encoding="utf-8"
    )

    docs = load_documents(str(doc_dir))

    assert len(docs) == 1
    assert docs[0].metadata["vendor_id"] == "VENDOR-A"
    assert docs[0].metadata["source"] == "vendor-a/sop.md"
    assert docs[0].metadata["doc_id"] == "vendor-a/sop.md:Perjanjian Vendor-A > MOQ"
    assert docs[0].id == docs[0].metadata["doc_id"]


def test_loader_file_datar_menurunkan_vendor_id_dari_nama_file(tmp_path):
    doc_dir = tmp_path / "sops"
    doc_dir.mkdir()
    (doc_dir / "vendor-b.md").write_text("MOQ 250 unit.", encoding="utf-8")

    docs = load_documents(str(doc_dir))

    assert len(docs) == 1
    assert docs[0].metadata["vendor_id"] == "VENDOR-B"


def test_loader_pdf_menghasilkan_chunk_dengan_section_halaman(tmp_path):
    doc_dir = tmp_path / "sops"
    (doc_dir / "vendor-b").mkdir(parents=True)
    (doc_dir / "vendor-b" / "sop.pdf").write_bytes(_minimal_pdf_bytes("MOQ 250 unit."))

    docs = load_documents(str(doc_dir))

    assert len(docs) >= 1
    assert docs[0].metadata["vendor_id"] == "VENDOR-B"
    assert docs[0].metadata["source"] == "vendor-b/sop.pdf"
    assert "halaman" in docs[0].metadata["section"]
    assert docs[0].metadata["doc_id"] == "vendor-b/sop.pdf:0"


def test_loader_menangani_dua_vendor_subfolder_tanpa_campur(tmp_path):
    doc_dir = tmp_path / "sops"
    for vendor in ("vendor-a", "vendor-b"):
        (doc_dir / vendor).mkdir(parents=True)
        (doc_dir / vendor / "sop.md").write_text(
            f"# Perjanjian {vendor}\n\n## MOQ\n\nMOQ {vendor} unit.\n", encoding="utf-8"
        )

    docs = load_documents(str(doc_dir))

    assert len(docs) == 2
    assert {d.metadata["vendor_id"] for d in docs} == {"VENDOR-A", "VENDOR-B"}
