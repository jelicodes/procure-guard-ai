# CONTEXT — Procure Guard AI

Single-context repo. Ringkasan domain dan keputusan arsitektur untuk navigasi agen.
ADR menyimpan keputusan arsitektur yang lebih rinci: lihat `docs/adr/`.

## Ringkasan

Procure Guard AI mengotomasi alur pengadaan barang kritis (low-stock crisis) dari
deteksi stok → ekstraksi aturan vendor (RAG SOP) → kalkulasi reorder → pembuatan
draft Purchase Order (PO) → persetujuan governansi → pengiriman ke ERP (mock, via
MCP protocol). Target bisnis: menurunkan waktu pemrosesan PO dari 24–72 jam menjadi
**< 5 menit** via deteksi otomatis, rekomendasi terkomputasi, dan approval 1-klik.

## Glossary

- **Krisis low-stock (low-stock crisis)** — kondisi saat `stock_level <= safety_stock`.
  Deteksi via scheduler scan atau pemicu manual.
- **SKU** — Stock Keeping Unit: identitas barang (`sku`), punya `stock_level`,
  `safety_stock`, `unit_price`, `reorder_point`, `avg_daily_usage`.
- **Vendor rules** — aturan pengadaan vendor (`VendorRules`): `moq`, `lead_time_days`,
  `discount_tiers`, `penalty_clauses`, `min_order_value`. Diambil dari SOP vendor via RAG.
- **Basis** — sumber aturan yang dipakai kalkulasi: `rag` (diekstrak dari SOP) atau
  `fallback` (nilai default saat ekstraksi gagal).
- **Reorder qty** — kuantitas pesanan yang dihitung deterministik:
  `max(moq, ceil(lead_time_days * avg_daily_usage - stock_level))`, dibulatkan ke tier
  diskon bila memungkinkan.
- **Purchase Order (PO)** — draft pesanan (`PurchaseOrder`): `po_no`, `sku`, `vendor_id`,
  `qty`, `unit_price`, `total_value`, `status`, `basis`, `explanation`.
- **Governansi approval** — PO dengan `total_value >= APPROVAL_THRESHOLD` (default 10.000)
  wajib persetujuan manusia (interrupt); di bawah ambang auto-lanjut ke ERP.
- **MCP ERP** — server MCP (FastMCP) yang membungkus mock Oracle ERP, mengekspos tools
  `get_inventory`, `create_po`, `get_po_status`. Kontrak integrasi ERP untuk backend.
- **Thread graph** — satu eksekusi pipeline LangGraph per scan, diidentifikasi `thread_id`,
  di-persist via checkpointer agar approval dapat di-resume asinkron.

## Arsitektur

Monorepo modular dengan unit berbatas jelas:

- `backend/` — FastAPI + LangGraph `StateGraph` (node: detector → vendor_rag →
  reorder_calc → po_builder → approver/erp_submit), RAG vendor SOP, scheduler APScheduler.
- `mcp_server/` — FastMCP server membungkus mock Oracle ERP (in-memory + seed).
- `frontend/` — React SPA (Vite, TypeScript, Tailwind CSS 4) dashboard + approval via REST + polling.
- `docker-compose.yml` — postgres(pgvector), mcp-server, backend, frontend.

Keputusan inti (detail di ADR):
- Abstraksi `build_vector_store()`: `InMemoryVectorStore` (dev/test) vs `PGVector` (prod),
  dipilih dari `DATABASE_URL`.
- Abstraksi `get_checkpointer()`: `InMemorySaver` (dev/test) vs `PostgresSaver` (prod).
- Human-in-the-loop memakai LangGraph `interrupt()` + resume `Command(resume=...)`.
- Bahasa: kode, docstring, UI, dan komentar **Bahasa Indonesia**; dokumentasi level
  proyek (README) boleh English untuk keperluan portfolio.