# Desain — Procure Guard AI: Automated Low-Stock Crisis & PO Governance

**Tanggal:** 2026-08-14
**Status:** Disetujui (review brainstorming)
**Versi:** V1.1

---

## 1. Ringkasan

Sistem **Procure Guard AI** mengotomasi alur pengadaan barang kritis (low-stock crisis)
dari deteksi stok → ekstraksi aturan vendor (RAG) → kalkulasi reorder → pembuatan
draft Purchase Order (PO) → persetujuan governansi → pengiriman ke ERP.

Target bisnis: menurunkan waktu pemrosesan PO dari **24–72 jam menjadi < 5 menit**
melalui deteksi otomatis, rekomendasi terkomputasi, dan approval 1-klik.

## 2. Cakupan V1

**In-scope (end-to-end, data simulasi):**

1. Deteksi low-stock otomatis (threshold `stock_level <= safety_stock`) via scheduler
   dan scan manual.
2. Ekstraksi aturan vendor (MOQ, lead time, diskon, penalti) dari PDF SOP/kontrak
   menggunakan RAG + structured output LLM.
3. Kalkulasi reorder quantity deterministik dengan mempertimbangkan MOQ, lead time,
   dan tier diskon.
4. Pembuatan draft PO otomatis.
5. Governansi approval: PO bernilai `>= $10.000` wajib persetujuan manajer
   (interrupt human-in-the-loop); PO di bawah ambang auto-lanjut.
6. Pengiriman draft PO ke ERP mock via MCP protocol (FastMCP server + MCP client
   di LangGraph).
7. Dashboard React untuk daftar krisis, detail PO + ringkasan alasan, tombol
   Approve/Reject 1-klik.
8. Audit trail setiap transisi state graph.

**Out-of-scope V1:** integrasi ERP Oracle produksi (mock hanya), auth/peran penuh
(stub saja), skala multi-gudang, riwayat pemakaian forecasting, notifikasi email/Slack.

## 3. Arsitektur

Monorepo modular dengan unit ber-batas jelas:

```
procure-guard-ai/
├── docker-compose.yml          # postgres (pgvector), mcp-server, backend, frontend
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI: approval, dashboard, scan
│   │   ├── agents/
│   │   │   ├── nodes/          # detector, vendor_rag, reorder_calc, po_builder, approver, erp_submit
│   │   │   ├── graph.py        # StateGraph + PostgresSaver checkpointer
│   │   │   └── state.py        # typed POGuardState
│   │   ├── mcp_client/         # MultiServerMCPClient → get_tools() ERP
│   │   ├── core/               # config, db (SQLAlchemy), models
│   │   ├── rag/                # ingest PDF → pgvector, retriever, VendorRules
│   │   ├── services/           # scheduler APScheduler, seed
│   │   └── schemas/            # Pydantic: PO, InventoryItem, ApprovalDecision
│   ├── data/                   # seed inventory, sample vendor PDFs
│   ├── tests/
│   └── pyproject.toml
├── mcp_server/
│   ├── erp_mcp.py              # FastMCP: get_inventory, create_po, get_po_status
│   └── mock_erp/               # mock Oracle ERP backend (in-memory + seed)
├── frontend/                   # React SPA (Vite)
└── docs/
```

### Prinsip

- Setiap unit punya satu tujuan, interface jelas, dan dapat diuji independen.
- Adapter ERP dan RAG diisolasi sehingga implementasi nyata (Oracle, penyedia lain)
  dapat mengganti mock tanpa mengubah graph.
- State graph dipersist via checkpointer agar approval dapat di-resume asinkron
  melalui API.

## 4. Tech Stack

| Lapisan | Pilihan | Alasan |
|---|---|---|
| LLM chat/reasoning | `ChatGroq` (`langchain-groq`, env `GROQ_API_KEY`) | Provider Groq (keputusan pengguna); mendukung `with_structured_output` dan `bind_tools` |
| Embedding RAG | `GoogleGenerativeAIEmbeddings` (`langchain-google-genai`, env `GOOGLE_API_KEY`) | Model Gemini Embedding didukung penuh di LangChain |
| Orkestrasi | LangGraph `StateGraph` + checkpointer | State machine + human-in-the-loop + resume asinkron |
| MCP server | FastMCP (`fastmcp`), transport `streamable-http` | Membungkus mock ERP menjadi MCP tools |
| MCP client | `langchain-mcp-adapters` `MultiServerMCPClient` | Konsumsi MCP tools di LangGraph |
| Backend API | FastAPI + uvicorn | Async, Pydantic-native |
| DB (dev/test) | SQLite (file-based) | Berjalan tanpa Docker di mesin pengembang |
| DB (produksi) | PostgreSQL + pgvector (via docker-compose) | Production-ready; ekstensi vector untuk RAG |
| ORM | SQLAlchemy 2.x | Migrasi mudah |
| Checkpointer | `MemorySaver`/`SqliteSaver` (dev), `PostgresSaver` (prod) | Resume HITL asinkron via API |
| Vector store | `InMemoryVectorStore` (dev/test), PGVector (prod) | Abstraksi `build_vector_store()` sesuai `DATABASE_URL` |
| Scheduler | APScheduler (in-process) | Interval scan, tanpa infra tambahan |
| Frontend | React + Vite (TypeScript) | SPA; REST + polling untuk daftar & approval (tanpa LangGraph Platform) |
| Deploy | docker-compose | 4 container |
| Tooling | pip + venv (Python), npm (frontend) | Tersedia di mesin pengembang |

## 5. Alur Data (Data Flow) & LangGraph State

### 5.1 LangGraph State

```python
class POGuardState(TypedDict):
    inventory: InventoryItem        # SKU, stock_level, safety_stock, unit_price
    vendor_rules: VendorRules | None  # hasil RAG
    reorder: ReorderCalc | None       # reorder_qty, total_value, basis
    po: PurchaseOrder | None          # draft PO
    approval: ApprovalDecision | None # approved/rejected, reviewer, note
    erp_ref: ERPRef | None            # no_po / status dari mock ERP
    error: str | None
```

Skema Pydantic utama:

- `InventoryItem`: `sku, name, vendor_id, stock_level, safety_stock, unit_price, reorder_point, avg_daily_usage`
- `VendorRules`: `vendor_id, sku, moq, lead_time_days, discount_tiers[], penalty_clauses[], min_order_value, basis`
- `ReorderCalc`: `sku, reorder_qty, total_value, explanation, basis`
- `PurchaseOrder`: `po_no, sku, vendor_id, qty, unit_price, total_value, line_items[], status, created_at`
- `ApprovalDecision`: `decision (approved|rejected), reviewer, note`

### 5.2 Graph

```
START → [detector] → [vendor_rag] → [reorder_calc] → [po_builder]
         po_builder: total >= $10k → interrupt() → [approver]
                     total <  $10k  → langsung [erp_submit]
         [approver] (resume Command) → [erp_submit] → END
```

- **detector**: baca stok dari MCP `get_inventory` (mock ERP); SKU dengan
  `stock_level <= safety_stock` diproses. Tanpa SKU kritis → END (idle).
- **vendor_rag**: retrieve chunks pgvector (by SKU/vendor) → `ChatGroq.with_structured_output(VendorRules)`.
  Gagal/tidak ada dokumen → `VendorRules` default (`moq=0, lead_time_days=7, basis="fallback"`).
- **reorder_calc**: deterministik `reorder_qty = max(moq, ceil((lead_time_days * avg_daily_usage) - stock_level))`
  dibulatkan ke tier diskon; hitung `total_value`.
- **po_builder**: susun `PurchaseOrder`; hitung total; route approval
  (`interrupt(po)` jika `total_value >= 10_000`, else auto).
- **approver**: hanya berjalan saat resume; validasi `ApprovalDecision`.
  `approved` → lanjut `erp_submit`; `rejected` → END dengan status PO `rejected`.
- **erp_submit**: panggil MCP tool `create_po` (mock ERP), simpan `erp_ref`.

### 5.3 Human-in-the-Loop

- Memakai LangGraph `interrupt()` + checkpointer (MemorySaver/SqliteSaver dev; PostgresSaver prod).
- Frontend memakai REST + polling: daftar PO berstatus `pending_approval` ditampilkan
  sebagai approval card; backend menampilkan ringkasan alasan & validasi SOP.
- Resume dilakukan backend: `POST /pos/{id}/approve` dan `/reject` meneruskan
  `Command(resume=ApprovalDecision)` ke thread graph.

## 6. Komponen RAG & MCP ERP

### 6.1 RAG Vendor SOP

- **Ingest** (CLI `python -m app.ingest --dir backend/data/`):
  `PyPDFLoader` → `RecursiveCharacterTextSplitter` (chunk ~800, overlap ~200) →
  `GoogleGenerativeAIEmbeddings` → simpan ke pgvector (tabel `vendor_documents`).
- **Retrieve**: query by SKU/vendor → top-k chunks → prompt + structured output → `VendorRules`.
- Metadata chunk: `vendor_id, sku, source_file`.

### 6.2 MCP ERP Server (`mcp_server/`)

FastMCP `erp_mcp.py`, transport `streamable-http`, port `8001/mcp`:

- `get_inventory() -> list[InventoryItem]`
- `create_po(draft_po: dict) -> {po_no, status}`
- `get_po_status(po_no: str) -> {po_no, status}`

`mock_erp/` menyimpan in-memory dict + seed data (20–50 SKU).

### 6.3 MCP Client (backend)

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "erp": {"transport": "http", "url": ERP_MCP_URL}
})
tools = await client.get_tools()
```

Tools di-inject ke node `detector` dan `erp_submit`.

## 7. FastAPI Endpoints

| Method | Path | Fungsi |
|---|---|---|
| GET | `/api/inventory` | Daftar stok & SKU kritis |
| POST | `/api/scan` | Trigger scan manual (panggil graph) |
| GET | `/api/pos` | Daftar PO + status |
| GET | `/api/pos/{id}` | Detail PO + ringkasan alasan (approval card) |
| POST | `/api/pos/{id}/approve` | Resume graph dengan `ApprovalDecision(approved)` |
| POST | `/api/pos/{id}/reject` | Resume graph dengan `ApprovalDecision(rejected)` |
| GET | `/api/approvals/pending` | Daftar PO menunggu approve |

## 8. Error Handling

| Skenario | Penanganan |
|---|---|
| MCP ERP down | Retry 2x; jika tetap gagal, PO disimpan status `pending_erp` (draft tidak hilang) |
| RAG retrieval gagal | Fallback `VendorRules` default, `basis="fallback"`; manajer diberi tanda |
| LLM timeout / structured output gagal | `max_retries`; retry 1x; lalu fallback parsing minimal |
| qty negatif / nilai invalid | Validasi domain di `reorder_calc` menolak |
| `ApprovalDecision` tidak valid | Validator hanya menerima `approved`/`rejected` + note opsional |
| Audit trail | Tabel `po_events` mencatat tiap transisi (timestamp, node, actor, note) |

## 9. Testing

| Jenis | Cakupan |
|---|---|
| Unit (pytest) | `reorder_calc` (MOQ/diskon/lead time), parsing `VendorRules`, state reducer |
| Integrasi | Pipeline end-to-end dengan MCP server in-proc (tanpa container): deteksi → RAG → kalkulasi → PO |
| API (pytest + httpx) | Endpoint approval, resume graph, list PO |
| Frontend (vitest + RTL) | Render approval card, aksi approve/reject |

## 10. Deployment (docker-compose)

4 service:

1. `postgres` — pgvector image; mount volume; init DB.
2. `mcp-server` — FastMCP, port `8001`.
3. `backend` — FastAPI/uvicorn, port `8000`, expose `/api`; menjalankan scheduler.
4. `frontend` — Vite dev server, port `5173`, reverse-proxy ke `/api`.

Env via `.env`: `GROQ_API_KEY`, `GOOGLE_API_KEY`, `DATABASE_URL`,
`ERP_MCP_URL` (`http://mcp-server:8001/mcp`).

## 11. Metrik Keberhasilan (V1)

1. **PO Processing Cycle Time:** dari deteksi hingga PO terbit di bawah 5 menit
   (menunggu approval saja).
2. **Stockout Frequency:** menurun (kuantitatif pada data simulasi).
3. **Procurement Staff Productivity:** hemat waktu admin (diasumsikan, ditandai
   pada demo).
4. **Governance visibility:** 100% PO >= $10.000 melalui approval card dengan
   ringkasan alasan & validasi SOP vendor.

## 12. Langkah Implementasi Berikutnya

1. Buat implementation plan via skill `writing-plans`.
2. Eksekusi: scaffolding repo, backend (core/db/schemas), RAG, MCP server, graph,
   API, scheduler, frontend, docker-compose, tests.
