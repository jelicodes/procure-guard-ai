"""Aplikasi FastAPI Procure Guard AI."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.deps import GraphDeps
from app.api.routes import router
from app.rag.retriever import VendorRetriever
from app.services.seed import seed_database


def create_app(deps: GraphDeps | None = None) -> FastAPI:
    app = FastAPI(title="Procure Guard AI", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.deps = deps
    app.include_router(router)
    return app


def create_default_app() -> FastAPI:
    """Versi produksi: membangun deps default (MCP http + retriever pgvector)."""
    from app.agents.deps import build_default_deps
    from app.core.llm import get_embeddings
    from app.rag.store import build_vector_store

    import asyncio

    store = build_vector_store(get_embeddings())
    retriever = VendorRetriever(store)
    deps = asyncio.run(build_default_deps(retriever))
    seed_database()
    return create_app(deps)


# Jangan bangun app default saat impor (tes/tooling) — butuh API key + handshake MCP.
# Bangun hanya untuk serving produksi dengan PROCURE_GUARD_APP=1.
app: FastAPI | None = create_default_app() if os.environ.get("PROCURE_GUARD_APP") == "1" else None