"""Loader dokumen SOP/kontrak vendor (PDF, Markdown, TXT)."""
from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def load_documents(directory: str) -> list[Document]:
    root = Path(directory)
    docs: list[Document] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".md", ".txt"}:
            docs.extend(TextLoader(str(path), encoding="utf-8").load())
        elif path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            docs.append(Document(page_content=text, metadata={"source": str(path)}))
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
    return splitter.split_documents(docs)