# Procure Guard AI — Panduan Pengembangan

## Arsitektur

- `backend/` — FastAPI + LangGraph (detector → vendor_rag → reorder_calc → po_builder → approver/erp_submit) + SQLAlchemy + SQLite (dev).
- `frontend/` — React SPA (Vite, TypeScript, Tailwind CSS v4). Dashboard inventori, observability agen, dan approval PO. Proksi `/api` → backend.
- `mcp_server/` — server MCP mock Oracle ERP (FastMCP, streamable-http).
- `docker-compose.yml` — postgres (pgvector), mcp-server, backend, frontend.

## Menjalankan

```bash
# Backend (dari backend/)
.venv\Scripts\python -m app                       # http://localhost:8000

# Frontend (dari frontend/)
npm run dev                                       # http://localhost:5173, proxy /api → :8000

# MCP ERP (dari root, sebelum backend bila ERP live dipakai)
backend\.venv\Scripts\python -m mcp_server.erp_mcp # http://localhost:8001/mcp
```

## Verifikasi

```bash
# Backend
cd backend && .venv\Scripts\python -m pytest

# Frontend
cd frontend && npm test
npm run build
```

Catatan: seluruh tes berjalan tanpa Docker maupun panggilan LLM/ERP live.