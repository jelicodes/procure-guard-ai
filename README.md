<div align="center">

# Procure Guard AI

**Intelligent low-stock detection → supplier-rule RAG → deterministic reorder → governed purchase orders → ERP via MCP**

Automates the critical procurement pipeline end-to-end, cutting purchase order cycle time from **24–72 hours to under 5 minutes**.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-000000?style=for-the-badge&logo=modelcontextprotocol&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL%2Bpgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

</div>

---

## Overview

Procure Guard AI is a **human-in-the-loop agentic workflow** that supervises a
company's procurement process from raw inventory signal to an approved, submitted
purchase order (PO):

```
Inventory scan  →  Supplier SOP (RAG)  →  Reorder math  →  Draft PO  →  Governance approval  →  ERP submission
```

It detects low-stock items, reads supplier terms (MOQ, lead time, volume discounts,
penalties) from SOP documents using retrieval-augmented generation, computes the
optimal reorder quantity deterministically, drafts a purchase order, and routes it
through an approval workflow — **high-value POs require a human manager's
one-click approval**, while routine POs flow straight through to the ERP.

The ERP integration is done over the **Model Context Protocol (MCP)** using FastMCP,
which cleanly decouples the orchestration logic from any specific ERP system.

---

## Key Features

| Feature | Description |
|---|---|
| **Automated low-stock detection** | Scheduled (APScheduler) + on-demand scans flag every item where `stock_level <= safety_stock`, ranked by severity. |
| **Supplier-rule extraction (RAG)** | Vendor SOP/contract documents are embedded (Gemini), retrieved per SKU, and parsed into structured `VendorRules` (MOQ, lead time, discount tiers, penalties) via LLM structured output. |
| **Deterministic reorder math** | `max(moq, ⌈lead_time × daily_usage − stock⌉)`, bumped to the nearest discount tier within headroom, fully unit-tested and explainable. |
| **Human-in-the-loop governance** | POs at or above a configurable threshold (`$10,000` default) pause the LangGraph with `interrupt()`; a manager approves or rejects with a one-click dashboard action, and the graph resumes asynchronously. |
| **ERP submission over MCP** | Draft POs are sent to a mock Oracle ERP through a FastMCP server (`get_inventory`, `create_po`, `get_po_status`). Swap the mock for a real ERP without touching the pipeline. |
| **Full audit trail** | Every state transition of the graph is persisted (`po_events`), and each run is resumable via a persisted checkpointer (`thread_id`). |
| **React dashboard** | Real-time view of pending approvals (with reasoning summary), the PO list, and one-click approve/reject — REST + polling. |

---

## Architecture

Modular monorepo with clean seams:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Frontend (React + Vite)                          │
│                        dashboard · one-click approval                       │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ REST /api (polling)
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                        Backend (FastAPI + LangGraph)                        │
│                                                                             │
│   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐   ┌───────────┐  │
│   │   detector   │──▶│   vendor_rag  │──▶│ reorder_calc │──▶│po_builder │  │
│   └──────────────┘   └───────────────┘   └──────────────┘   └─────┬─────┘  │
│                                                                    │        │
│                                                   total ≥ threshold?│       │
│                                                              ▲      ▼       │
│                                                              │  ┌────────┐  │
│                                              resume ────────┴──│approver│  │  ◀── human-in-the-loop
│                                                              │  └────┬───┘  │      (interrupt + resume)
│                                                              └──────▼──────┘
│                                                                    │        │
│   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐   ┌─────▼─────┐  │
│   │  Postgres /  │   │   vector store │   │  checkpointer│   │erp_submit │  │
│   │  SQLite      │   │  InMemory/PG   │   │ InMemory/PG  │   └─────┬─────┘  │
│   └──────────────┘   └───────────────┘   └──────────────┘         │        │
└───────────────────────────────────┬─────────────────────────────────┼────────┘
                                    │        MCP tools (streamable-http / stdio)
┌───────────────────────────────────▼─────────────────────────────────▼────────┐
│                    mcp_server (FastMCP) wrapping mock Oracle ERP              │
│                        get_inventory · create_po · get_po_status              │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Design principles**

- **Deep, testable modules** — each pipeline node is a pure function factory with
  injected dependencies; the whole graph is exercised without any live LLM/ERP calls.
- **Swappable infrastructure** — `build_vector_store()` and `get_checkpointer()`
  return in-memory implementations for dev/tests and PostgreSQL/pgvector versions
  for production, selected purely from `DATABASE_URL`.
- **ERP-agnostic** — the backend consumes ERP capabilities as MCP *tools*, never a
  vendor SDK. The mock is replaceable by any MCP server.
- **Explainable decisions** — every PO carries a `basis` (`rag` or `fallback`) and a
  human-readable `explanation` of the reorder math, shown in the approval UI.

See [`CONTEXT.md`](CONTEXT.md) and [`docs/adr/0001-arsitektur-v1.md`](docs/adr/0001-arsitektur-v1.md)
for domain vocabulary and architectural decisions.

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Orchestration | **LangGraph** (`StateGraph` + checkpointer) | State machine, `interrupt()`/resume for human-in-the-loop |
| LLM / reasoning | **Groq** `ChatGroq` (`llama-3.1-8b-instant`) | Structured output for `VendorRules` extraction |
| Embeddings | **Google Gemini** `gemini-embedding-001` | Document vectors for RAG |
| MCP server | **FastMCP** (`streamable-http` / `stdio`) | Mock Oracle ERP as MCP tools |
| MCP client | **LangChain MCP Adapters** (`MultiServerMCPClient`) | ERP tools consumed inside the graph |
| API | **FastAPI** + Uvicorn | Async, Pydantic-native |
| ORM | **SQLAlchemy 2.x** | `inventory_items`, `purchase_orders`, `po_events` |
| Vector store | **InMemoryVectorStore** (dev) / **PGVector** (prod) | Selected by `DATABASE_URL` |
| Checkpointer | **InMemorySaver** (dev) / **PostgresSaver** (prod) | Async approval resume |
| Database | **SQLite** (dev) / **PostgreSQL 16 + pgvector** (prod) | |
| Scheduler | **APScheduler** | Interval-based stock scans |
| Frontend | **React 18 + Vite + TypeScript**, Vitest + Testing Library | REST + polling |
| Deploy | **docker-compose** | 4 services: postgres, mcp-server, backend, frontend |

---

## Getting Started

### Prerequisites

- Python **3.11+** (pip + venv; no uv required)
- Node.js **18+** (npm)
- API keys: **GROQ_API_KEY** and **GOOGLE_API_KEY**
- Docker (optional, for the production stack)

### 1. Environment

Copy the template and fill in your keys:

```bash
cp .env.example .env
```

```
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key
DATABASE_URL=sqlite:///./procure_guard.db
ERP_MCP_URL=http://mcp-server:8001/mcp
ERP_MCP_TRANSPORT=http
APPROVAL_THRESHOLD=10000.0
SCAN_INTERVAL_MINUTES=60
```

> Settings are read from `.env` **relative to the working directory** (pydantic
> `env_file=".env"`). Run commands from `backend/` or place the file there.

### 2. Local development (no Docker)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e .        # Windows
# .venv/bin/python -m pip install -e .         # Linux/macOS
```

Ingest the vendor SOPs into the vector store (requires `GOOGLE_API_KEY`):

```bash
.venv\Scripts\python -m app.cli ingest --dir data/vendor_sops
```

Start the **MCP ERP server first** (the backend connects to it at startup), in a
separate terminal from the repo root:

```bash
backend\.venv\Scripts\python -m mcp_server.erp_mcp     # http://localhost:8001/mcp
```

Start the API (FastAPI on :8000 + scheduler):

```bash
cd backend
.venv\Scripts\python -m app
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev                                             # :5173, proxies /api → :8000
```

### 3. Production / Docker

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| MCP ERP | http://localhost:8001/mcp |
| PostgreSQL | localhost:5432 |

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/scan` | Trigger a low-stock scan (also runs on the scheduler) |
| `GET` | `/api/pos` | List all purchase orders |
| `GET` | `/api/pos/{po_no}` | Single purchase order |
| `POST` | `/api/pos/{po_no}/approve` | Approve a pending PO (resumes the graph) |
| `POST` | `/api/pos/{po_no}/reject` | Reject a pending PO, with optional note |
| `GET` | `/api/approvals/pending` | POs awaiting human approval |
| `GET` | `/api/health` | Liveness probe |

---

## Testing

```bash
# Backend — 43 tests (unit, integration, API)
cd backend && .\.venv\Scripts\python -m pytest

# Frontend — 3 tests
cd frontend && npm test
```

The backend test suite runs **entirely without Docker or live LLM/ERP calls** —
infrastructure is injected and the MCP server is exercised over stdio.

---

## Project Structure

```
procure-guard-ai/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routes: scan, PO list, approvals
│   │   ├── agents/         # LangGraph state, nodes, graph, deps
│   │   ├── mcp_client/     # MCP client gateway → ERP tools
│   │   ├── core/           # config, db, models, checkpointer, llm
│   │   ├── rag/            # loader, vector store, retriever, extractor
│   │   ├── services/       # reorder math, seed, scheduler
│   │   └── schemas/        # Pydantic domain objects
│   ├── data/               # seed inventory + sample vendor SOPs
│   └── tests/              # unit · integration · api
├── mcp_server/             # FastMCP server wrapping mock Oracle ERP
├── frontend/               # React SPA (Vite, TypeScript)
├── docs/                   # spec, plan, research, ADRs
├── CONTEXT.md              # domain glossary & architecture
└── docker-compose.yml      # postgres · mcp-server · backend · frontend
```

---

## Roadmap (post-V1)

- Real Oracle ERP integration (replace the MCP mock — no pipeline changes needed)
- Full authentication & role-based access (manager/admin)
- Multi-warehouse inventory support
- Demand forecasting from usage history
- Email/Slack notifications for pending approvals

---

## License

Private project — part of the author's portfolio.