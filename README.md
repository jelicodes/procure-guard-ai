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
