# Procure Guard AI

Otomatisasi low-stock crisis → rekomendasi reorder (RAG SOP vendor) → draft PO →
approval governansi 1-klik → kirim ke mock ERP via MCP protocol.

Lihat `docs/superpowers/specs/2026-08-14-procure-guard-po-governance-design.md` untuk desain
lengkap dan `docs/superpowers/plans/2026-08-14-procure-guard-po-governance.md` untuk rencana
implementasi.

## Struktur

- `backend/` — FastAPI + LangGraph, memakai MCP client ke ERP
- `mcp_server/` — FastMCP server yang membungkus mock Oracle ERP
- `frontend/` — React SPA untuk dashboard & approval
- `docker-compose.yml` — postgres(pgvector), mcp-server, backend, frontend

## Menjalankan (dev)

Backend:

1. `cd backend && python -m venv .venv`
2. `.venv\Scripts\python -m pip install -e .` (Windows) / `.venv/bin/python -m pip install -e .` (Linux)
3. Salin `.env.example` (root repo) ke `backend/.env`, lalu isi `GROQ_API_KEY` dan `GOOGLE_API_KEY`.
   Catatan: settings dibaca dari `.env` relatif terhadap direktori kerja (pydantic `env_file=".env"`),
   jadi saat menjalankan dari `backend/` file `.env` harus ada di dalam `backend/`.
   Pastikan juga `ERP_MCP_URL=http://localhost:8001/mcp` (bukan hostname docker `mcp-server`).
4. Ingest SOP vendor: `.venv\Scripts\python -m app.cli ingest --dir data/vendor_sops`
5. Jalankan MCP server (dev tanpa Docker) dari root repo, di terminal terpisah:
   `backend\.venv\Scripts\python -m mcp_server.erp_mcp` — FastMCP streamable-http diekspos
   pada `http://localhost:8001/mcp`. MCP server HARUS hidup sebelum langkah 6 karena backend
   menyambung ke `ERP_MCP_URL` saat start (build deps).
6. Jalankan API: `.venv\Scripts\python -m app` (FastAPI :8000 + scheduler scan)

Frontend:

1. `cd frontend && npm install`
2. `npm run dev` (:5173, proxy `/api` ke :8000)

## Menjalankan (produksi / Docker)

```
docker compose up --build
```

- Backend memakai `env_file: .env` root repo — pastikan root `.env` berisi `GROQ_API_KEY`, `GOOGLE_API_KEY`.
- `mcp-server` diekspos pada `:8001/mcp` (streamable-http), `backend` pada :8000, `frontend` pada :5173, `postgres` pada :5432.
- Bila menjalankan `erp_mcp.py` manual, sesuaikan `ERP_MCP_URL` (docker: `http://mcp-server:8001/mcp`).
