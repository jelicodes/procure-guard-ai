# ADR-0001 — Arsitektur V1: Orkestrasi LangGraph, MCP ERP, dan Abstraksi Runtime

- **Status:** Accepted (2026-08-15)
- **Konteks:** Spesifikasi V1 `docs/superpowers/specs/2026-08-14-procure-guard-po-governance-design.md`
  disetujui. ADR ini merekam keputusan arsitektur yang sudah diimplementasi agar keputusan
  dan alasannya terdokumentasi untuk navigasi agen dan review masa depan.

## Keputusan

### 1. Orkestrasi pipeline memakai LangGraph `StateGraph` + checkpointer

Pipeline PO governance direpresentasikan sebagai state machine:
`START → detector → vendor_rag → reorder_calc → po_builder → (approver) → erp_submit → END`.

- State `POGuardState` (TypedDict, `total=False`): `inventory`, `vendor_rules`, `reorder`,
  `po`, `approval`, `erp_po_no`, `error`.
- Approval memakai `interrupt()`; resume asinkron via `Command(resume=ApprovalDecision)`.
- Checkpointer dipilih lewat `get_checkpointer()`: `InMemorySaver` (dev/test) vs
  `PostgresSaver` (prod, `langgraph-checkpoint-postgres` + `psycopg[binary]`).
- Graph di-cache per instance `GraphDeps` (kunci `id(deps)`) agar checkpointer InMemory
  tidak dibuat ulang antar call scan/resume — tanpa ini state thread hilang.

**Alasan:** membutuhkan human-in-the-loop + resume asinkron lewat API; state machine
eksplisit memudahkan audit trail dan penambahan node.

### 2. ERP diakses via MCP protocol, bukan library/SDK langsung

`mcp_server/` (FastMCP, transport `streamable-http` default, `stdio` untuk dev/test)
membungkus mock Oracle ERP menjadi tools: `get_inventory`, `create_po`, `get_po_status`.
Backend memakai `langchain-mcp-adapters.MultiServerMCPClient` untuk mengkonsumsi tools
tersebut di dalam node graph (`app/mcp_client/erp.py`).

**Alasan:** memisahkan ERP dari graph — mengganti mock dengan Oracle nyata tidak mengubah
logika pipeline; MCP memberi kontrak tools yang stabil dan dapat diuji (`InMemory` ERP +
inject tools untuk unit test).

### 3. Abstraksi runtime lewat `build_vector_store()` dan `get_checkpointer()`

Pilihan penyimpanan ditentukan dari `DATABASE_URL`:

| `DATABASE_URL` | Vector store | Checkpointer |
|---|---|---|
| `sqlite:///...` (dev/test) | `InMemoryVectorStore` | `InMemorySaver` |
| `postgresql+psycopg://...` (prod) | `PGVector` | `PostgresSaver` |

**Alasan:** mesin dev tidak punya Docker/Postgres; seluruh tes harus jalan penuh tanpa
Postgres, sementara produksi memakai PostgreSQL + pgvector.

### 4. Governansi approval berbasis ambang nilai

PO dengan `total_value >= APPROVAL_THRESHOLD` (default `10000.0`) wajib `interrupt()`;
di bawah ambang auto-lanjut ke ERP. `APPROVAL_THRESHOLD=1000` di `backend/.env` adalah
override dev-only supaya alur approval teruji di smoke test; produksi tetap `10000.0`.

**Alasan:** kebutuhan bisnis — PO bernilai besar butuh persetujuan manajer; nilai kecil
boleh otomatis untuk memangkas cycle time.

### 5. Bahasa: Indonesia untuk kode, English opsional untuk dokumentasi eksternal

Kode, docstring, UI, dan komentar memakai Bahasa Indonesia. README (dokumentasi level
proyek) boleh English untuk keperluan portfolio/recruiter.

**Alasan:** konvensi tim; README English memperluas jangkauan pembaca.

## Konsekuensi

- Menambah node = menambah node LangGraph + edge; state harus tetap `total=False`.
- Mengganti ERP nyata = implementasi server MCP baru, tanpa perubahan graph.
- Checkpointer InMemory tidak persisten antar proses (dev-only).
- Tidak ada migrasi DB versi; `Base.metadata.create_all` dipakai (V1).