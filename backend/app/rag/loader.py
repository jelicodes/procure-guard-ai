"""Loader dokumen SOP/kontrak vendor (PDF, Markdown, TXT) dengan metadata kaya."""
from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from pypdf import PdfReader

HEADERS_TO_SPLIT_ON = [("#", "H1"), ("##", "H2")]


def _derive_vendor_id(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    if len(rel.parts) > 1:
        return rel.parts[0].upper()
    return path.stem.upper()


def _section_from_meta(meta: dict) -> str:
    return " > ".join(str(meta[k]) for k in ("H1", "H2") if meta.get(k))


def _contextualize(chunk: Document, section: str, source: str) -> Document:
    """Context-prepend: menambahkan jalur section di depan konten chunk agar
    embedding tidak terenceri banyak SKU (varian nol-LLM dari contextual retrieval)."""
    if section:
        chunk.page_content = f"[{source} | {section}] {chunk.page_content}"
    return chunk


def _load_markdown(path: Path, vendor_id: str, source: str) -> list[Document]:
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS_TO_SPLIT_ON)
    chunks = splitter.split_text(path.read_text(encoding="utf-8"))
    docs: list[Document] = []
    for idx, chunk in enumerate(chunks):
        section = _section_from_meta(chunk.metadata)
        doc_id = f"{source}:{section}" if section else f"{source}:{idx}"
        chunk.metadata.update(
            {
                "vendor_id": vendor_id,
                "source": source,
                "section": section,
                "doc_id": doc_id,
            }
        )
        chunk.id = doc_id
        _contextualize(chunk, section, source)
        docs.append(chunk)
    return docs


def _load_pdf(path: Path, vendor_id: str, source: str) -> list[Document]:
    reader = PdfReader(str(path))
    pages = [
        Document(
            page_content=page.extract_text() or "",
            metadata={"source": source, "page": i},
        )
        for i, page in enumerate(reader.pages)
    ]
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
    chunks = splitter.split_documents(pages)
    for idx, chunk in enumerate(chunks):
        doc_id = f"{source}:{idx}"
        section = f"halaman {chunk.metadata.get('page', '?')}"
        chunk.metadata.update(
            {
                "vendor_id": vendor_id,
                "section": section,
                "doc_id": doc_id,
            }
        )
        chunk.id = doc_id
        _contextualize(chunk, section, source)
    return chunks


def load_documents(directory: str) -> list[Document]:
    root = Path(directory)
    docs: list[Document] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        source = path.relative_to(root).as_posix()
        vendor_id = _derive_vendor_id(root, path)
        suffix = path.suffix.lower()
        if suffix in {".md", ".txt"}:
            docs.extend(_load_markdown(path, vendor_id, source))
        elif suffix == ".pdf":
            docs.extend(_load_pdf(path, vendor_id, source))
    return docs