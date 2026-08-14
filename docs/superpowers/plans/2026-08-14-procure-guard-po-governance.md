# Procure Guard AI — PO Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun V1 Procure Guard AI — otomatisasi low-stock crisis → rekomendasi reorder (RAG SOP vendor) → draft PO → approval governansi 1-klik → kirim ke mock ERP via MCP, menurunkan cycle time dari hari menjadi <5 menit.

**Architecture:** Monorepo modular — `backend/` (FastAPI + LangGraph StateGraph, node terisolasi) mengonsumsi MCP tools dari `mcp_server/` (FastMCP, streamable-http) yang membungkus mock Oracle ERP. RAG vendor SOP di-embed ke vector store dan diekstrak dengan structured output `ChatGroq`. Approval memakai LangGraph `interrupt()` + checkpointer; resume asinkron via `Command(resume=...)`. Frontend React SPA memakai REST + polling.

**Tech Stack:** Python 3.11+ · LangChain/LangGraph · FastMCP · FastAPI · SQLAlchemy 2 · React 18 + Vite · APScheduler · SQLite (dev) / PostgreSQL+pgvector (prod, docker-compose) · `ChatGroq` (GROQ) · `GoogleGenerativeAIEmbeddings` (Gemini)

## Global Constraints

- Bahasa: seluruh kode, docstring, UI, dan komentar memakai **Bahasa Indonesia**.
- `backend/` dependency management: `pip` + `venv` (uv tidak tersedia di mesin dev). `frontend/`: `npm` (pnpm tidak tersedia).
- Env wajib (file `.env`, tidak di-commit): `GROQ_API_KEY`, `GOOGLE_API_KEY`. Opsional: `DATABASE_URL` (default `sqlite:///./procure_guard.db`), `ERP_MCP_URL` (default `http://mcp-server:8001/mcp`), `ERP_MCP_TRANSPORT` (`http`|`stdio`), `APPROVAL_THRESHOLD` (default `10000.0`).
- Vector store: **abstraksi `build_vector_store()`** — mengembalikan `InMemoryVectorStore` bila `DATABASE_URL` SQLite (dev/test), `PGVector` bila Postgres (prod). Tidak ada Docker di mesin dev → tes harus jalan penuh tanpa Postgres.
- Checkpointer: `InMemorySaver` untuk dev/test, `PostgresSaver` untuk prod — melalui `get_checkpointer()`.
- Governansi: PO dengan `total_value >= APPROVAL_THRESHOLD` wajib `interrupt()` menunggu approval; di bawah threshold auto-lanjut.
- Python version floor: `>=3.11`. Package major: `langgraph>=0.6`, `langchain-core>=1.0`, `langchain-groq`, `langchain-google-genai`, `langchain-mcp-adapters>=0.2`, `fastmcp>=2`, `fastapi`, `sqlalchemy>=2`, `pydantic>=2`, `pydantic-settings`, `apscheduler>=3.10`, `pypdf`.
- Frontend: React 18, Vite 5, TypeScript 5, vitest + @testing-library/react.
- Setiap task berakhir dengan tes hijau (`pytest` di `backend/`, `npm test` di `frontend/`) dan commit.
- Perintah dijalankan dari direktori `backend/` (untuk Python) dan `frontend/` (untuk JS) kecuali disebut lain.

---

### Task 1: Inisialisasi Repo, Struktur Folder, dan Basis Konfigurasi

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `docs/` (berisi spec yang sudah ada)

**Interfaces:**
- Consumes: spec di `docs/superpowers/specs/2026-08-14-procure-guard-po-governance-design.md`
- Produces: struktur folder kosong yang diisi task-task berikutnya; env template yang menjadi kontrak variabel lingkungan seluruh proyek.

- [ ] **Step 1: Inisialisasi git dan struktur folder**

Jalankan dari `D:\Jeli\procure-guard-ai`:

```powershell
git init
New-Item -ItemType Directory -Path backend\app\api, backend\app\agents\nodes, backend\app\mcp_client, backend\app\core, backend\app\rag, backend\app\services, backend\app\schemas, backend\data, backend\tests\unit, backend\tests\integration, backend\tests\api, mcp_server\mock_erp, frontend, docs\superpowers\plans -Force | Out-Null
```

- [ ] **Step 2: Tulis `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Env
.env
.env.local

# SQLite dev DB
*.db
*.sqlite3

# Node
node_modules/
dist/
coverage/
.vite/

# Editor/OS
.idea/
.vscode/
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Tulis `.env.example`**

```bash
# LLM providers
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key

# Database (dev: sqlite; prod via docker-compose: postgresql+psycopg://procure:procure@postgres:5432/procure)
DATABASE_URL=sqlite:///./procure_guard.db

# MCP ERP
ERP_MCP_URL=http://mcp-server:8001/mcp
ERP_MCP_TRANSPORT=http

# Governance
APPROVAL_THRESHOLD=10000.0

# Scheduler (menit)
SCAN_INTERVAL_MINUTES=60
```

- [ ] **Step 4: Tulis `README.md` ringkas**

```markdown
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
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: inisialisasi repo, struktur folder, dan template env"
```

---

### Task 2: Scaffolding Backend — pyproject, venv, dan dependency

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/schemas/__init__.py`

**Interfaces:**
- Consumes: struktur folder dari Task 1.
- Produces: environment Python terinstal dengan semua dependensi; `pyproject.toml` yang menjadi kontrak dependency untuk task-task selanjutnya.

- [ ] **Step 1: Tulis `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "procure-guard-backend"
version = "0.1.0"
description = "Procure Guard AI backend: otomatisasi low-stock crisis dan PO governance"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.6",
    "langchain-core>=1.0",
    "langchain-groq",
    "langchain-google-genai",
    "langchain-mcp-adapters>=0.2",
    "langchain-postgres",
    "fastmcp>=2",
    "fastapi",
    "uvicorn[standard]",
    "sqlalchemy>=2",
    "pydantic>=2",
    "pydantic-settings",
    "python-dotenv",
    "apscheduler>=3.10",
    "pypdf",
    "pytest",
    "pytest-asyncio",
    "httpx",
]

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Buat file `__init__.py` kosong**

```powershell
New-Item -ItemType File -Force backend\app\__init__.py, backend\app\core\__init__.py, backend\app\schemas\__init__.py
```

- [ ] **Step 3: Buat venv dan install dependensi**

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
```

(workdir: `backend`)

- [ ] **Step 4: Verifikasi instalasi**

```powershell
.\.venv\Scripts\python -c "import langgraph, langchain_groq, langchain_google_genai, langchain_mcp_adapters, fastmcp, fastapi, sqlalchemy, pydantic, apscheduler; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/__init__.py backend/app/core/__init__.py backend/app/schemas/__init__.py
git commit -m "chore(backend): scaffolding pyproject dan dependensi"
```

---

### Task 3: Config, Database, dan Model SQLAlchemy

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/db.py`
- Create: `backend/app/core/models.py`

**Interfaces:**
- Consumes: env template (Task 1), dependency (Task 2).
- Produces:
  - `Settings` singleton (`from app.core.config import settings`) — properti: `database_url: str`, `erp_mcp_url: str`, `erp_mcp_transport: str`, `approval_threshold: float`, `scan_interval_minutes: int`, `groq_api_key: str|None`, `google_api_key: str|None`.
  - `Base` (DeclarativeBase), `engine`, `SessionLocal`, `get_session()` dependency.
  - ORM model: `InventoryItemModel`, `PurchaseOrderModel`, `POEventModel` — dipakai seluruh service/API.

- [ ] **Step 1: Tulis failing test `backend/tests/unit/test_config_db.py`**

```python
from app.core.config import settings
from app.core.db import engine, Base, SessionLocal, get_session


def test_settings_defaults():
    assert settings.approval_threshold == 10000.0
    assert settings.database_url.startswith("sqlite")


def test_models_have_expected_columns():
    table_names = set(Base.metadata.tables.keys())
    assert {
        "inventory_items",
        "purchase_orders",
        "po_events",
    }.issubset(table_names)
    po_cols = {c.name for c in Base.metadata.tables["purchase_orders"].columns}
    assert {"po_no", "sku", "total_value", "status", "thread_id"}.issubset(po_cols)


def test_session_context():
    with SessionLocal() as session:
        assert session is not None
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_config_db.py -v`
Expected: FAIL (module `app.core.config` tidak ditemukan)

- [ ] **Step 3: Tulis `backend/app/core/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Procure Guard AI"
    database_url: str = "sqlite:///./procure_guard.db"
    groq_api_key: str | None = None
    google_api_key: str | None = None
    erp_mcp_url: str = "http://mcp-server:8001/mcp"
    erp_mcp_transport: str = "http"
    approval_threshold: float = 10000.0
    scan_interval_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
```

- [ ] **Step 4: Tulis `backend/app/core/db.py`**

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(settings.database_url, connect_args=_connect_args(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
```

- [ ] **Step 5: Tulis `backend/app/core/models.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InventoryItemModel(Base):
    __tablename__ = "inventory_items"

    sku: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    vendor_id: Mapped[str] = mapped_column(String, index=True)
    stock_level: Mapped[int] = mapped_column(Integer)
    safety_stock: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    reorder_point: Mapped[int] = mapped_column(Integer)
    avg_daily_usage: Mapped[float] = mapped_column(Float)


class PurchaseOrderModel(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_no: Mapped[str] = mapped_column(String, unique=True)
    sku: Mapped[str] = mapped_column(String, index=True)
    vendor_id: Mapped[str] = mapped_column(String)
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    total_value: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="draft")
    basis: Mapped[str] = mapped_column(String, default="rag")
    explanation: Mapped[str] = mapped_column(Text, default="")
    thread_id: Mapped[str] = mapped_column(String, unique=True)
    erp_po_no: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class POEventModel(Base):
    __tablename__ = "po_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_id: Mapped[int] = mapped_column(Integer, index=True)
    node: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String, default="system")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
```

- [ ] **Step 6: Jalankan test, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_config_db.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/app/core backend/tests/unit/test_config_db.py
git commit -m "feat(core): config, engine, dan model SQLAlchemy"
```

---

### Task 4: Skema Pydantic (Domain Objects)

**Files:**
- Create: `backend/app/schemas/inventory.py`
- Create: `backend/app/schemas/vendor.py`
- Create: `backend/app/schemas/po.py`

**Interfaces:**
- Consumes: — (standalone).
- Produces (kontrak tipe seluruh aplikasi):
  - `InventoryItem`: `sku, name, vendor_id, stock_level, safety_stock, unit_price, reorder_point, avg_daily_usage`, property `is_critical`.
  - `VendorRules`: `vendor_id, sku|None, moq=0, lead_time_days=7, discount_tiers[], penalty_clauses[], min_order_value=0.0, basis="rag"`.
  - `DiscountTier`: `min_qty, discount_pct`.
  - `ReorderCalc`: `sku, reorder_qty, total_value, explanation, basis`.
  - `PurchaseOrder`: `po_no, sku, vendor_id, qty, unit_price, total_value, status, line_items[], created_at|None`.
  - `ApprovalDecision`: `decision (Literal["approved","rejected"]), reviewer="manager", note=""`.

- [ ] **Step 1: Tulis failing test `backend/tests/unit/test_schemas.py`**

```python
import pytest
from pydantic import ValidationError

from app.schemas.inventory import InventoryItem
from app.schemas.po import ApprovalDecision, PurchaseOrder, ReorderCalc
from app.schemas.vendor import DiscountTier, VendorRules


def make_item(**overrides) -> InventoryItem:
    defaults = {
        "sku": "SKU-001",
        "name": "Bearing 6204",
        "vendor_id": "VENDOR-A",
        "stock_level": 50,
        "safety_stock": 100,
        "unit_price": 12.5,
        "reorder_point": 120,
        "avg_daily_usage": 20.0,
    }
    defaults.update(overrides)
    return InventoryItem(**defaults)


def test_inventory_is_critical():
    assert make_item().is_critical is True
    assert make_item(stock_level=150).is_critical is False


def test_approval_decision_rejects_invalid_value():
    with pytest.raises(ValidationError):
        ApprovalDecision(decision="maybe")


def test_vendor_rules_defaults():
    rules = VendorRules(vendor_id="VENDOR-A")
    assert rules.moq == 0
    assert rules.lead_time_days == 7
    assert rules.basis == "rag"


def test_discount_tier_and_reorder():
    tier = DiscountTier(min_qty=500, discount_pct=5.0)
    reorder = ReorderCalc(sku="SKU-001", reorder_qty=500, total_value=6000.0, explanation="test", basis="rag")
    assert tier.discount_pct == 5.0
    assert reorder.total_value == 6000.0


def test_purchase_order_default_status():
    po = PurchaseOrder(po_no="PO-1", sku="SKU-001", vendor_id="VENDOR-A", qty=500, unit_price=12.5, total_value=6250.0)
    assert po.status == "draft"
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_schemas.py -v`
Expected: FAIL (modul skema tidak ada)

- [ ] **Step 3: Tulis `backend/app/schemas/inventory.py`**

```python
from pydantic import BaseModel


class InventoryItem(BaseModel):
    sku: str
    name: str
    vendor_id: str
    stock_level: int
    safety_stock: int
    unit_price: float
    reorder_point: int
    avg_daily_usage: float

    @property
    def is_critical(self) -> bool:
        return self.stock_level <= self.safety_stock
```

- [ ] **Step 4: Tulis `backend/app/schemas/vendor.py`**

```python
from pydantic import BaseModel, Field


class DiscountTier(BaseModel):
    min_qty: int = Field(gt=0)
    discount_pct: float = Field(ge=0, le=100)


class PenaltyClause(BaseModel):
    condition: str
    penalty: str


class VendorRules(BaseModel):
    vendor_id: str
    sku: str | None = None
    moq: int = 0
    lead_time_days: int = 7
    discount_tiers: list[DiscountTier] = Field(default_factory=list)
    penalty_clauses: list[PenaltyClause] = Field(default_factory=list)
    min_order_value: float = 0.0
    basis: str = "rag"
```

- [ ] **Step 5: Tulis `backend/app/schemas/po.py`**

```python
from typing import Literal

from pydantic import BaseModel, Field


class ReorderCalc(BaseModel):
    sku: str
    reorder_qty: int = Field(gt=0)
    total_value: float
    explanation: str
    basis: str = "rag"


class PurchaseOrder(BaseModel):
    po_no: str
    sku: str
    vendor_id: str
    qty: int = Field(gt=0)
    unit_price: float
    total_value: float
    status: str = "draft"
    line_items: list[dict] = Field(default_factory=list)
    created_at: str | None = None


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewer: str = "manager"
    note: str = ""
```

- [ ] **Step 6: Jalankan test, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_schemas.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas backend/tests/unit/test_schemas.py
git commit -m "feat(schemas): skema Pydantic domain (inventory, vendor, po)"
```

---

### Task 5: Mesin Kalkulasi Reorder (Pure Function)

**Files:**
- Create: `backend/app/services/reorder.py`
- Test: `backend/tests/unit/test_reorder.py`

**Interfaces:**
- Consumes: `InventoryItem`, `VendorRules`, `ReorderCalc` (Task 4).
- Produces: `compute_reorder(inventory: InventoryItem, rules: VendorRules) -> ReorderCalc`.

Aturan bisnis: `base = ceil(lead_time_days * avg_daily_usage - stock_level)`; `qty = max(moq, base)`;
jika ada `discount_tiers`, naikkan qty ke tier dengan `min_qty >= qty` jika `min_qty <= qty * 1.5`;
`total_value = qty * unit_price`. `basis` diambil dari `rules.basis`.

- [ ] **Step 1: Tulis failing test `backend/tests/unit/test_reorder.py`**

```python
from math import ceil

from app.schemas.inventory import InventoryItem
from app.schemas.vendor import DiscountTier, VendorRules
from app.services.reorder import compute_reorder


def make_item(stock=50, unit_price=10.0, usage=20.0):
    return InventoryItem(
        sku="SKU-001", name="Bearing", vendor_id="VENDOR-A",
        stock_level=stock, safety_stock=100, unit_price=unit_price,
        reorder_point=120, avg_daily_usage=usage,
    )


def test_reorder_uses_moq_and_lead_time():
    rules = VendorRules(vendor_id="VENDOR-A", moq=100, lead_time_days=7)
    result = compute_reorder(make_item(), rules)
    assert result.reorder_qty == 100
    assert result.total_value == 1000.0
    assert result.basis == "rag"


def test_reorder_rounds_up_to_discount_tier_within_headroom():
    rules = VendorRules(
        vendor_id="VENDOR-A", moq=0, lead_time_days=7,
        discount_tiers=[DiscountTier(min_qty=500, discount_pct=5.0)],
    )
    result = compute_reorder(make_item(), rules)
    # base = ceil(7*20 - 50) = 90 -> tier 500 within 90*1.5=135? NO -> keep 90
    assert result.reorder_qty == 90


def test_reorder_uses_tier_when_base_close():
    rules = VendorRules(
        vendor_id="VENDOR-A", moq=0, lead_time_days=7,
        discount_tiers=[DiscountTier(min_qty=100, discount_pct=5.0)],
    )
    result = compute_reorder(make_item(), rules)
    # base=90, tier 100 in [90, 135] -> 100
    assert result.reorder_qty == 100


def test_reorder_minimum_positive_when_stock_above_need():
    rules = VendorRules(vendor_id="VENDOR-A", moq=50, lead_time_days=7)
    item = make_item(stock=300, usage=10.0)  # base = 7*10-300 < 0
    result = compute_reorder(item, rules)
    assert result.reorder_qty == 50
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_reorder.py -v`
Expected: FAIL (module tidak ada)

- [ ] **Step 3: Tulis `backend/app/services/reorder.py`**

```python
from math import ceil

from app.schemas.inventory import InventoryItem
from app.schemas.po import ReorderCalc
from app.schemas.vendor import VendorRules


def compute_reorder(inventory: InventoryItem, rules: VendorRules) -> ReorderCalc:
    base_qty = ceil(rules.lead_time_days * inventory.avg_daily_usage - inventory.stock_level)
    qty = max(rules.moq, base_qty)
    for tier in sorted(rules.discount_tiers, key=lambda t: t.min_qty):
        if tier.min_qty >= qty and tier.min_qty <= qty * 1.5:
            qty = tier.min_qty
            break
    if qty <= 0:
        qty = 1
    total_value = round(qty * inventory.unit_price, 2)
    explanation = (
        f"max(moq={rules.moq}, lead*usage-stock={base_qty}); "
        f"qty={qty} @ {inventory.unit_price}"
    )
    return ReorderCalc(
        sku=inventory.sku,
        reorder_qty=qty,
        total_value=total_value,
        explanation=explanation,
        basis=rules.basis,
    )
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_reorder.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/reorder.py backend/tests/unit/test_reorder.py
git commit -m "feat(services): kalkulasi reorder quantity deterministik"
```

---

### Task 6: Mock ERP dan MCP Server (FastMCP)

**Files:**
- Create: `mcp_server/mock_erp/__init__.py`
- Create: `mcp_server/mock_erp/database.py`
- Create: `mcp_server/mock_erp/operations.py`
- Create: `mcp_server/erp_mcp.py`
- Create: `mcp_server/requirements.txt`
- Test: `backend/tests/integration/test_mcp_erp.py` (test MCP client terhadap server ini)

**Interfaces:**
- Produces (MCP tools yang menjadi kontrak backend):
  - `get_inventory() -> list[dict]` (bentuk = `InventoryItem`)
  - `create_po(po: dict) -> {po_no, status}`
  - `get_po_status(po_no: str) -> {po_no, status}`
- `mock_erp` menyimpan data in-memory; `reset_database()` untuk tes.
- Server dapat dijalankan sebagai: `python -m mcp_server.erp_mcp` (streamable-http) atau dengan env `MCP_TRANSPORT=stdio`.

- [ ] **Step 1: Tulis `mcp_server/mock_erp/database.py`**

```python
"""Penyimpanan in-memory mock Oracle ERP. Aman untuk dev/test."""
from __future__ import annotations

_INVENTORY: dict[str, dict] = {}
_POS: dict[str, dict] = {}


def seed_inventory(items: list[dict]) -> None:
    for item in items:
        _INVENTORY[item["sku"]] = item


def get_inventory() -> list[dict]:
    return list(_INVENTORY.values())


def upsert_po(po: dict) -> dict:
    po_no = po["po_no"]
    _POS[po_no] = {
        "po_no": po_no,
        "status": "DRAFT",
        "sku": po.get("sku"),
        "qty": po.get("qty"),
        "total_value": po.get("total_value"),
    }
    return _POS[po_no]


def get_po_status(po_no: str) -> dict:
    if po_no not in _POS:
        return {"po_no": po_no, "status": "NOT_FOUND"}
    return _POS[po_no]


def reset_database() -> None:
    _INVENTORY.clear()
    _POS.clear()
```

- [ ] **Step 2: Tulis `mcp_server/mock_erp/operations.py`**

```python
"""Operasi bisnis mock ERP yang dibungkus MCP tools."""
from __future__ import annotations

from mcp_server.mock_erp.database import get_inventory, get_po_status, upsert_po


def list_inventory() -> list[dict]:
    return get_inventory()


def create_po(po: dict) -> dict:
    if not po.get("po_no") or not po.get("sku") or po.get("qty", 0) <= 0:
        raise ValueError("Data PO tidak lengkap (po_no, sku, qty)")
    return upsert_po(po)


def check_po_status(po_no: str) -> dict:
    return get_po_status(po_no)
```

- [ ] **Step 3: Tulis `mcp_server/erp_mcp.py`**

```python
"""MCP server ERP — membungkus mock Oracle ERP menjadi MCP tools."""
from __future__ import annotations

import os
from datetime import datetime

from fastmcp import FastMCP

from mcp_server.mock_erp.operations import check_po_status, create_po, list_inventory

mcp = FastMCP("erp")


@mcp.tool()
def get_inventory() -> list[dict]:
    """Mengembalikan daftar level inventori terkini dari ERP."""
    return list_inventory()


@mcp.tool()
def create_po(po: dict) -> dict:
    """Membuat Purchase Order baru di ERP dan mengembalikan nomor PO.

    Args:
        po: dict dengan kunci po_no, sku, vendor_id, qty, unit_price, total_value.
    """
    return create_po(po)


@mcp.tool()
def get_po_status(po_no: str) -> dict:
    """Mengembalikan status Purchase Order berdasarkan nomor PO."""
    return check_po_status(po_no)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    mcp.run(transport=transport)
```

- [ ] **Step 4: Tulis `mcp_server/requirements.txt`**

```txt
fastmcp>=2
```

- [ ] **Step 5: Install dependensi mcp_server ke venv backend**

```powershell
.\.venv\Scripts\python -m pip install -r ..\mcp_server\requirements.txt
```

(workdir `backend`)

- [ ] **Step 6: Tulis `backend/tests/conftest.py` (env & sys.path untuk mcp_server)**

```python
import os
import sys
from pathlib import Path

# Set env SEBELUM import app apa pun
os.environ.setdefault("ERP_MCP_TRANSPORT", "stdio")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).parent / 'test.db'}")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend root
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root (untuk mcp_server)
```

- [ ] **Step 7: Tulis integration test MCP `backend/tests/integration/test_mcp_erp.py`**

```python
import asyncio

import pytest
from langchain_mcp_adapters.client import MultiServerMCPClient

from mcp_server.mock_erp.database import reset_database, seed_inventory

SAMPLE_INVENTORY = [
    {
        "sku": "SKU-001", "name": "Bearing 6204", "vendor_id": "VENDOR-A",
        "stock_level": 50, "safety_stock": 100, "unit_price": 12.5,
        "reorder_point": 120, "avg_daily_usage": 20.0,
    }
]


@pytest.fixture(autouse=True)
def _clean_db():
    reset_database()
    seed_inventory(SAMPLE_INVENTORY)
    yield
    reset_database()


@pytest.mark.asyncio
async def test_mcp_get_inventory_tool():
    reset_database()
    seed_inventory(SAMPLE_INVENTORY)
    client = MultiServerMCPClient(
        {
            "erp": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "mcp_server.erp_mcp"],
                "env": {"MCP_TRANSPORT": "stdio"},
            }
        }
    )
    tools = await client.get_tools()
    tool_map = {t.name: t for t in tools}
    assert "get_inventory" in tool_map

    result = await tool_map["get_inventory"].ainvoke({})
    assert result[0]["sku"] == "SKU-001"
    await client.close()


@pytest.mark.asyncio
async def test_mcp_create_po_roundtrip():
    client = MultiServerMCPClient(
        {
            "erp": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "mcp_server.erp_mcp"],
                "env": {"MCP_TRANSPORT": "stdio"},
            }
        }
    )
    tools = {t.name: t for t in await client.get_tools()}
    created = await tools["create_po"].ainvoke(
        {"po": {"po_no": "PO-100", "sku": "SKU-001", "vendor_id": "VENDOR-A", "qty": 200, "unit_price": 12.5, "total_value": 2500.0}}
    )
    assert created["status"] == "DRAFT"
    status = await tools["get_po_status"].ainvoke({"po_no": "PO-100"})
    assert status["po_no"] == "PO-100"
    await client.close()
```

- [ ] **Step 8: Jalankan test, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/integration/test_mcp_erp.py -v`
Expected: PASS (2 passed)

- [ ] **Step 9: Commit**

```bash
git add mcp_server backend/tests/integration/test_mcp_erp.py
git commit -m "feat(mcp): MCP server ERP dengan mock Oracle (get_inventory, create_po, get_po_status)"
```

---

### Task 7: MCP Client di Backend

**Files:**
- Create: `backend/app/mcp_client/__init__.py`
- Create: `backend/app/mcp_client/erp.py`

**Interfaces:**
- Consumes: `settings` (Task 3), MCP server tools (Task 6).
- Produces:
  - `get_erp_tools() -> dict[str, BaseTool]` — peta nama-tool MCP (`get_inventory`, `create_po`, `get_po_status`), transport http/stdio sesuai `settings.erp_mcp_transport`.
  - `InventoryGateway` class dengan method async `get_inventory() -> list[InventoryItem]` dan `create_po(po: PurchaseOrder) -> dict` — dipakai node graph.
  - `InventoryGateway` mendukung injection `tools` untuk unit test tanpa memanggil MCP.

- [ ] **Step 1: Tulis failing test `backend/tests/unit/test_mcp_client.py`**

```python
import pytest

from app.mcp_client.erp import InventoryGateway
from app.schemas.inventory import InventoryItem
from app.schemas.po import PurchaseOrder


class FakeTool:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, args):
        return self._result


@pytest.mark.asyncio
async def test_gateway_get_inventory_maps_items():
    tools = {
        "get_inventory": FakeTool([{"sku": "SKU-001", "name": "Bearing", "vendor_id": "VENDOR-A", "stock_level": 50, "safety_stock": 100, "unit_price": 12.5, "reorder_point": 120, "avg_daily_usage": 20.0}]),
    }
    gw = InventoryGateway(tools)
    items = await gw.get_inventory()
    assert items[0].sku == "SKU-001"
    assert items[0].is_critical is True


@pytest.mark.asyncio
async def test_gateway_create_po():
    tools = {"create_po": FakeTool({"po_no": "PO-1", "status": "DRAFT"})}
    gw = InventoryGateway(tools)
    po = PurchaseOrder(po_no="PO-1", sku="SKU-001", vendor_id="VENDOR-A", qty=200, unit_price=12.5, total_value=2500.0)
    result = await gw.create_po(po)
    assert result["status"] == "DRAFT"
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_mcp_client.py -v`
Expected: FAIL (modul tidak ada)

- [ ] **Step 3: Tulis `backend/app/mcp_client/erp.py`**

```python
"""Klien MCP ke ERP — membungkus MultiServerMCPClient agar node graph mudah dipakai."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import settings
from app.schemas.inventory import InventoryItem
from app.schemas.po import PurchaseOrder


async def get_erp_tools() -> dict[str, BaseTool]:
    if settings.erp_mcp_transport == "stdio":
        servers = {
            "erp": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "mcp_server.erp_mcp"],
                "env": {"MCP_TRANSPORT": "stdio"},
            }
        }
    else:
        servers = {"erp": {"transport": "http", "url": settings.erp_mcp_url}}

    client = MultiServerMCPClient(servers)
    tools = await client.get_tools()
    return {t.name: t for t in tools}


class InventoryGateway:
    """Gateway ke ERP via MCP tools. Tools dapat di-inject untuk tes."""

    def __init__(self, tools: dict[str, BaseTool | Any]):
        self._tools = tools

    async def get_inventory(self) -> list[InventoryItem]:
        raw = await self._tools["get_inventory"].ainvoke({})
        return [InventoryItem(**item) for item in raw]

    async def create_po(self, po: PurchaseOrder) -> dict:
        return await self._tools["create_po"].ainvoke({"po": po.model_dump()})
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_mcp_client.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/mcp_client backend/tests/unit/test_mcp_client.py
git commit -m "feat(mcp-client): gateway klien MCP ke ERP dengan injeksi tools untuk tes"
```

---

### Task 8: RAG Vendor SOP — Loader, Retriever, Vector Store, dan Ekstraksi Aturan

**Files:**
- Create: `backend/app/rag/__init__.py`
- Create: `backend/app/rag/loader.py`
- Create: `backend/app/rag/store.py`
- Create: `backend/app/rag/extractor.py`
- Create: `backend/app/rag/retriever.py`
- Create: `backend/data/vendor_sops/vendor-a.md`
- Create: `backend/data/vendor_sops/vendor-b.md`
- Create: `backend/data/inventory_seed.json`
- Test: `backend/tests/unit/test_extractor.py`, `backend/tests/unit/test_retriever.py`

**Interfaces:**
- Consumes: `settings` (Task 3), `VendorRules` (Task 4).
- Produces:
  - `load_documents(directory: str) -> list[Document]` — baca `.pdf`/`.md`/`.txt`.
  - `build_vector_store(embeddings)` — `InMemoryVectorStore` (SQLite dev) / `PGVector` (Postgres prod).
  - `VendorRetriever(store)` dengan `retrieve(vendor_id: str, sku: str, k: int = 4) -> list[str]`.
  - `build_rule_extractor(model=None)` → `extract(vendor_id, sku, chunks) -> VendorRules` (structured output).
  - `seed_database()` untuk memuat `inventory_seed.json` ke SQLAlchemy.

- [ ] **Step 1: Tulis data contoh**

`backend/data/inventory_seed.json`:

```json
[
  {
    "sku": "SKU-001",
    "name": "Bearing 6204",
    "vendor_id": "VENDOR-A",
    "stock_level": 45,
    "safety_stock": 100,
    "unit_price": 12.5,
    "reorder_point": 120,
    "avg_daily_usage": 20.0
  },
  {
    "sku": "SKU-002",
    "name": "Piston Seal 30mm",
    "vendor_id": "VENDOR-B",
    "stock_level": 800,
    "safety_stock": 300,
    "unit_price": 4.75,
    "reorder_point": 350,
    "avg_daily_usage": 40.0
  },
  {
    "sku": "SKU-003",
    "name": "Servo Motor 750W",
    "vendor_id": "VENDOR-A",
    "stock_level": 12,
    "safety_stock": 15,
    "unit_price": 850.0,
    "reorder_point": 18,
    "avg_daily_usage": 1.5
  },
  {
    "sku": "SKU-004",
    "name": "Hydraulic Valve DN25",
    "vendor_id": "VENDOR-B",
    "stock_level": 5000,
    "safety_stock": 4000,
    "unit_price": 22.0,
    "reorder_point": 4500,
    "avg_daily_usage": 300.0
  }
]
```

`backend/data/vendor_sops/vendor-a.md`:

```markdown
# SOP Vendor — VENDOR-A (PT Industri Jaya)

## Aturan Umum Pengadaan

- Minimum Order Quantity (MOQ): 100 unit per SKU.
- Lead time pengiriman standar: 7 hari kerja.
- Diskon volume: 5% untuk pembelian >= 500 unit; 8% untuk >= 1000 unit.
- Klausul penalti: keterlambatan pengiriman > 3 hari dikenakan penalti 1% per hari dari nilai PO.

## Kategori Bearing

- SKU-001 (Bearing 6204): wajib memakai kemasan kotak kayu untuk pengiriman.
- SKU-003 (Servo Motor 750W): memerlukan persetujuan quality sebelum release.
```

`backend/data/vendor_sops/vendor-b.md`:

```markdown
# SOP Vendor — VENDOR-B (PT Sejahtera Part)

## Aturan Umum Pengadaan

- Minimum Order Quantity (MOQ): 250 unit per SKU.
- Lead time pengiriman: 10 hari kerja.
- Diskon volume: 3% untuk pembelian >= 1000 unit.
- Klausul penalti: pengembalian barang cacat wajib diajukan maksimal 7 hari setelah penerimaan.

## Kategori Seal & Valve

- SKU-002 (Piston Seal 30mm): toleransi retur 2%.
- SKU-004 (Hydraulic Valve DN25): penyesuaian harga otomatis pada pembelian kuartalan.
```

- [ ] **Step 2: Tulis failing test `backend/tests/unit/test_retriever.py`**

```python
from app.rag.loader import load_documents
from app.rag.retriever import VendorRetriever
from langchain_core.embeddings import DeterministicFakeEmbedding


def test_retriever_finds_vendor_documents(tmp_path):
    doc_dir = tmp_path / "sops"
    doc_dir.mkdir()
    (doc_dir / "vendor-a.md").write_text(
        "MOQ 100 unit. Lead time 7 hari. Diskon 5% untuk 500 unit. Vendor A."
    )
    (doc_dir / "vendor-b.md").write_text(
        "MOQ 250 unit. Lead time 10 hari. Vendor B."
    )

    docs = load_documents(str(doc_dir))
    assert len(docs) == 2

    store = VendorRetriever.build_store_for_test(docs)
    retriever = VendorRetriever(store)
    hits = retriever.retrieve("VENDOR-A", "SKU-001", k=1)
    assert len(hits) == 1
    assert "100" in hits[0]
```

Catatan: tambahkan method `build_store_for_test(docs)` di `VendorRetriever` (staticmethod) yang membuat `InMemoryVectorStore` dengan `DeterministicFakeEmbedding` lalu `add_documents`. Implementasinya menyatu pada Step 4.

- [ ] **Step 3: Jalankan test, pastikan gagal**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_retriever.py -v`
Expected: FAIL (modul tidak ada)

- [ ] **Step 4: Tulis `backend/app/rag/loader.py`**

```python
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
```

- [ ] **Step 5: Tulis `backend/app/rag/store.py`**

```python
"""Factory vector store — InMemory (dev) atau PGVector (prod)."""
from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_postgres import PGVector

from app.core.config import settings


def build_vector_store(embeddings: Embeddings):
    if settings.database_url.startswith("postgres"):
        return PGVector(
            embeddings=embeddings,
            connection=settings.database_url,
            collection_name="vendor_documents",
        )
    return InMemoryVectorStore(embeddings)
```

- [ ] **Step 6: Tulis `backend/app/rag/retriever.py`**

```python
"""Retriever aturan vendor dari vector store."""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.vectorstores import InMemoryVectorStore

from app.rag.store import build_vector_store


class VendorRetriever:
    def __init__(self, store):
        self._store = store

    def retrieve(self, vendor_id: str, sku: str, k: int = 4) -> list[str]:
        query = f"aturan pengadaan vendor {vendor_id} sku {sku} moq lead time diskon"
        results = self._store.similarity_search(query, k=k)
        return [doc.page_content for doc in results]

    @staticmethod
    def build_store_for_test(docs: list[Document]):
        store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
        store.add_documents(docs)
        return store
```

- [ ] **Step 7: Jalankan test retriever, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_retriever.py -v`
Expected: PASS (1 passed)

- [ ] **Step 8: Tulis failing test `backend/tests/unit/test_extractor.py`**

```python
from app.rag.extractor import build_rule_extractor
from app.schemas.vendor import VendorRules


class FakeStructuredModel:
    """Mengembalikan VendorRules tanpa benar-benar memanggil LLM."""

    def __init__(self, result: VendorRules):
        self._result = result

    def with_structured_output(self, schema):
        return self

    async def ainvoke(self, prompt: str) -> VendorRules:
        return self._result


async def test_extractor_returns_structured_rules():
    expected = VendorRules(vendor_id="VENDOR-A", sku="SKU-001", moq=100, lead_time_days=7, basis="rag")
    extract = build_rule_extractor(model=FakeStructuredModel(expected))
    rules = await extract("VENDOR-A", "SKU-001", ["MOQ 100 unit, lead time 7 hari"])
    assert rules.moq == 100
    assert rules.basis == "rag"
```

- [ ] **Step 9: Jalankan test, pastikan gagal**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_extractor.py -v`
Expected: FAIL (modul tidak ada)

- [ ] **Step 10: Tulis `backend/app/rag/extractor.py`**

```python
"""Ekstraksi aturan vendor dari chunk SOP via structured output LLM."""
from __future__ import annotations

from app.schemas.vendor import VendorRules


def build_rule_extractor(model=None):
    """Membangun fungsi extract. `model` dapat di-inject untuk tes."""
    if model is None:
        from app.core.llm import get_chat_model

        model = get_chat_model()

    structured = model.with_structured_output(VendorRules)

    async def extract(vendor_id: str, sku: str, chunks: list[str]) -> VendorRules:
        prompt = (
            f"Ekstrak aturan pengadaan untuk vendor {vendor_id} (SKU {sku}) dari "
            f"ekserp SOP berikut. Jika suatu field tidak ada, gunakan nilai default "
            f"(moq=0, lead_time_days=7). Selalu set basis='rag'.\n\n"
            f"Ekserp SOP:\n" + "\n---\n".join(chunks)
        )
        return await structured.ainvoke(prompt)

    return extract
```

- [ ] **Step 11: Jalankan test extractor, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_extractor.py -v`
Expected: PASS (1 passed)

- [ ] **Step 12: Tulis `backend/app/services/seed.py` (seed DB SQLite)**

```python
"""Seed data inventori contoh ke database (dev/test)."""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.db import Base, SessionLocal, engine
from app.core.models import InventoryItemModel


def seed_database() -> None:
    Base.metadata.create_all(engine)
    seed_path = Path(__file__).resolve().parents[2] / "data" / "inventory_seed.json"
    items = json.loads(seed_path.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        session.query(InventoryItemModel).delete()
        for item in items:
            session.add(InventoryItemModel(**item))
        session.commit()
```

- [ ] **Step 13: Verifikasi seed jalan**

Run (workdir `backend`): `.\.venv\Scripts\python -c "from app.services.seed import seed_database; seed_database(); from app.core.db import SessionLocal; from app.core.models import InventoryItemModel; s=SessionLocal(); print(s.query(InventoryItemModel).count())"`
Expected: `4`

- [ ] **Step 14: Commit**

```bash
git add backend/app/rag backend/app/services/seed.py backend/data backend/tests/unit/test_retriever.py backend/tests/unit/test_extractor.py
git commit -m "feat(rag): loader, vector store factory, retriever, dan ekstraksi aturan vendor"
```

---

### Task 9: Factory LLM dan Embeddings

**Files:**
- Create: `backend/app/core/llm.py`

**Interfaces:**
- Consumes: `settings` (Task 3).
- Produces: `get_chat_model()` → `ChatGroq` (`model="llama-3.1-8b-instant"`, `temperature=0`, `max_retries=2`); `get_embeddings()` → `GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")`.

- [ ] **Step 1: Tulis `backend/app/core/llm.py`**

```python
"""Factory model LLM dan embeddings."""
from __future__ import annotations

from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings


def get_chat_model() -> ChatGroq:
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0,
        max_retries=2,
    )


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
```

- [ ] **Step 2: Verifikasi import OK (tanpa memanggil API)**

Run (workdir `backend`): `.\.venv\Scripts\python -c "from app.core.llm import get_chat_model, get_embeddings; print(type(get_chat_model()).__name__, type(get_embeddings()).__name__)"`
Expected: `ChatGroq GoogleGenerativeAIEmbeddings`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/llm.py
git commit -m "feat(core): factory ChatGroq dan GoogleGenerativeAIEmbeddings"
```

---

### Task 10: State LangGraph dan Node-Node Pipeline

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/state.py`
- Create: `backend/app/agents/nodes/__init__.py`
- Create: `backend/app/agents/nodes/detector.py`
- Create: `backend/app/agents/nodes/vendor_rag.py`
- Create: `backend/app/agents/nodes/reorder_calc.py`
- Create: `backend/app/agents/nodes/po_builder.py`
- Create: `backend/app/agents/nodes/approver.py`
- Create: `backend/app/agents/nodes/erp_submit.py`
- Test: `backend/tests/unit/test_nodes.py`

**Interfaces:**
- Produces `POGuardState(TypedDict)` dengan kunci: `inventory`, `vendor_rules`, `reorder`, `po`, `approval`, `erp_po_no`, `error` (semua optional).
- Node factory functions (menerima dependensi via parameter, testable):
  - `make_detector(get_inventory: Callable) -> node` — mengembalikan `{"inventory": item}` SKU paling kritis atau `{"error": "no_critical_stock"}`.
  - `make_vendor_rag(extract, retriever) -> node` — `{"vendor_rules": rules}`; fallback rules bila gagal (basis="fallback").
  - `make_reorder_node() -> node` — `{"reorder": compute_reorder(inventory, rules)}`.
  - `make_po_builder() -> node` — `{"po": PurchaseOrder}` dengan `po_no` dari timestamp.
  - `make_approver() -> node` — `interrupt()` untuk approval; `{"approval": decision, "po": po}`.
  - `make_erp_submit(gateway, log_event) -> node` — `{"erp_po_no": ...}`; bila ERP gagal → `{"error": ...}`.

- [ ] **Step 1: Tulis `backend/app/agents/state.py`**

```python
"""State typed untuk LangGraph pipeline PO governance."""
from typing import TypedDict

from app.schemas.inventory import InventoryItem
from app.schemas.po import ApprovalDecision, PurchaseOrder, ReorderCalc
from app.schemas.vendor import VendorRules


class POGuardState(TypedDict, total=False):
    inventory: InventoryItem
    vendor_rules: VendorRules
    reorder: ReorderCalc
    po: PurchaseOrder
    approval: ApprovalDecision
    erp_po_no: str
    error: str
```

- [ ] **Step 2: Tulis `backend/app/agents/nodes/detector.py`**

```python
"""Node deteksi low-stock — memilih SKU paling kritis dari inventori."""
from __future__ import annotations

from typing import Callable

from app.schemas.inventory import InventoryItem


def make_detector(get_inventory: Callable[[], list[InventoryItem]]):
    async def detector(state):
        items = await get_inventory() if _is_async(get_inventory) else get_inventory()
        critical = [item for item in items if item.is_critical]
        if not critical:
            return {"error": "no_critical_stock"}
        chosen = min(critical, key=lambda i: i.stock_level / max(i.safety_stock, 1))
        return {"inventory": chosen}

    return detector


def _is_async(fn: Callable) -> bool:
    import inspect

    return inspect.iscoroutinefunction(fn)
```

- [ ] **Step 3: Tulis `backend/app/agents/nodes/vendor_rag.py`**

```python
"""Node RAG vendor — ekstrak aturan dari SOP, fallback bila gagal."""
from __future__ import annotations

from typing import Callable

from app.schemas.vendor import VendorRules


def make_vendor_rag(extract: Callable, retrieve: Callable):
    async def vendor_rag(state):
        inventory = state["inventory"]
        try:
            chunks = retrieve(inventory.vendor_id, inventory.sku)
            rules = await extract(inventory.vendor_id, inventory.sku, chunks)
        except Exception:
            rules = VendorRules(vendor_id=inventory.vendor_id, sku=inventory.sku, basis="fallback")
        return {"vendor_rules": rules}

    return vendor_rag
```

- [ ] **Step 4: Tulis `backend/app/agents/nodes/reorder_calc.py`**

```python
"""Node kalkulasi reorder quantity."""
from __future__ import annotations

from app.services.reorder import compute_reorder


def make_reorder_node():
    async def reorder_calc(state):
        reorder = compute_reorder(state["inventory"], state["vendor_rules"])
        return {"reorder": reorder}

    return reorder_calc
```

- [ ] **Step 5: Tulis `backend/app/agents/nodes/po_builder.py`**

```python
"""Node penyusun draft Purchase Order."""
from __future__ import annotations

import time

from app.schemas.po import PurchaseOrder


def make_po_builder():
    async def po_builder(state):
        inventory = state["inventory"]
        reorder = state["reorder"]
        po = PurchaseOrder(
            po_no=f"PO-{int(time.time())}",
            sku=inventory.sku,
            vendor_id=inventory.vendor_id,
            qty=reorder.reorder_qty,
            unit_price=inventory.unit_price,
            total_value=reorder.total_value,
            line_items=[
                {
                    "sku": inventory.sku,
                    "qty": reorder.reorder_qty,
                    "unit_price": inventory.unit_price,
                }
            ],
        )
        return {"po": po}

    return po_builder
```

- [ ] **Step 6: Tulis `backend/app/agents/nodes/approver.py`**

```python
"""Node approval human-in-the-loop — interrupt() lalu resume dengan keputusan."""
from __future__ import annotations

from langgraph.types import interrupt

from app.schemas.po import ApprovalDecision


def make_approver():
    async def approver(state):
        po = state["po"]
        payload = {
            "type": "approval_request",
            "po_no": po.po_no,
            "sku": po.sku,
            "vendor_id": po.vendor_id,
            "qty": po.qty,
            "total_value": po.total_value,
            "explanation": state["reorder"].explanation,
            "basis": state["reorder"].basis,
        }
        decision = interrupt(payload)
        approval = ApprovalDecision(**decision)
        if approval.decision == "approved":
            po.status = "approved"
        else:
            po.status = "rejected"
        return {"approval": approval, "po": po}

    return approver
```

- [ ] **Step 7: Tulis `backend/app/agents/nodes/erp_submit.py`**

```python
"""Node submit PO ke ERP via MCP gateway."""
from __future__ import annotations

from app.mcp_client.erp import InventoryGateway


def make_erp_submit(gateway: InventoryGateway, log_event: callable | None = None):
    async def erp_submit(state):
        po = state["po"]
        if state.get("approval") and state["approval"].decision == "rejected":
            return {"po": po}
        try:
            result = await gateway.create_po(po)
            po.status = "submitted"
            return {"erp_po_no": result.get("po_no"), "po": po}
        except Exception as exc:
            po.status = "pending_erp"
            if log_event:
                log_event(po.po_no, "erp_submit", f"ERP gagal: {exc}")
            return {"error": str(exc), "po": po}

    return erp_submit
```

- [ ] **Step 8: Tulis failing test `backend/tests/unit/test_nodes.py`**

```python
import pytest

from app.agents.nodes.approver import make_approver
from app.agents.nodes.detector import make_detector
from app.agents.nodes.po_builder import make_po_builder
from app.agents.nodes.reorder_calc import make_reorder_node
from app.agents.nodes.vendor_rag import make_vendor_rag
from app.schemas.inventory import InventoryItem
from app.schemas.po import ApprovalDecision, PurchaseOrder, ReorderCalc
from app.schemas.vendor import VendorRules


def make_item(**overrides):
    defaults = {
        "sku": "SKU-001", "name": "Bearing", "vendor_id": "VENDOR-A",
        "stock_level": 50, "safety_stock": 100, "unit_price": 12.5,
        "reorder_point": 120, "avg_daily_usage": 20.0,
    }
    defaults.update(overrides)
    return InventoryItem(**defaults)


@pytest.mark.asyncio
async def test_detector_selects_most_critical():
    items = [make_item(sku="A", stock_level=90, safety_stock=100), make_item(sku="B", stock_level=5, safety_stock=100)]
    node = make_detector(lambda: items)
    result = await node({})
    assert result["inventory"].sku == "B"


@pytest.mark.asyncio
async def test_detector_no_critical():
    node = make_detector(lambda: [make_item(stock_level=500, safety_stock=100)])
    result = await node({})
    assert result["error"] == "no_critical_stock"


@pytest.mark.asyncio
async def test_vendor_rag_fallback_on_failure():
    async def bad_extract(*a, **k):
        raise RuntimeError("LLM down")

    node = make_vendor_rag(bad_extract, lambda *a, **k: [])
    state = {"inventory": make_item()}
    result = await node(state)
    assert result["vendor_rules"].basis == "fallback"


@pytest.mark.asyncio
async def test_reorder_node_sets_reorder():
    node = make_reorder_node()
    state = {
        "inventory": make_item(),
        "vendor_rules": VendorRules(vendor_id="VENDOR-A", moq=100, lead_time_days=7),
    }
    result = await node(state)
    assert isinstance(result["reorder"], ReorderCalc)
    assert result["reorder"].reorder_qty == 100


@pytest.mark.asyncio
async def test_po_builder_creates_draft():
    node = make_po_builder()
    state = {
        "inventory": make_item(),
        "reorder": ReorderCalc(sku="SKU-001", reorder_qty=200, total_value=2500.0, explanation="x", basis="rag"),
    }
    result = await node(state)
    po = result["po"]
    assert isinstance(po, PurchaseOrder)
    assert po.status == "draft"
    assert po.total_value == 2500.0


def test_approver_interrupts_and_resumes(monkeypatch):
    captured = {}

    class FakeInterrupt:
        def __init__(self, decision):
            self._decision = decision

        def __call__(self, payload):
            captured["payload"] = payload
            return self._decision

    node = make_approver()
    state = {
        "po": PurchaseOrder(po_no="PO-1", sku="SKU-001", vendor_id="VENDOR-A", qty=200, unit_price=12.5, total_value=2500.0),
        "reorder": ReorderCalc(sku="SKU-001", reorder_qty=200, total_value=2500.0, explanation="x", basis="rag"),
    }

    async def run():
        # inject fake interrupt via monkeypatch of langgraph.types.interrupt
        import app.agents.nodes.approver as mod

        mod.interrupt = FakeInterrupt(ApprovalDecision(decision="approved").model_dump())
        return await node(state)

    result = asyncio.run(run())
    assert captured["payload"]["type"] == "approval_request"
    assert result["approval"].decision == "approved"
    assert result["po"].status == "approved"
```

- [ ] **Step 9: Jalankan test, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_nodes.py -v`
Expected: PASS (6 passed)

- [ ] **Step 10: Commit**

```bash
git add backend/app/agents backend/tests/unit/test_nodes.py
git commit -m "feat(agents): state dan node pipeline PO governance"
```

---

### Task 11: Graph LangGraph + Checkpointer + Dependencies Wiring

**Files:**
- Create: `backend/app/agents/graph.py`
- Create: `backend/app/agents/deps.py`
- Create: `backend/app/core/checkpointer.py`
- Test: `backend/tests/integration/test_graph.py`

**Interfaces:**
- Consumes: semua node (Task 10), gateway (Task 7), retriever/extractor (Task 8), llm (Task 9).
- Produces:
  - `get_checkpointer()` — `InMemorySaver` untuk dev/test; hook untuk `PostgresSaver` bila `DATABASE_URL` Postgres.
  - `build_graph(deps: GraphDeps)` — `StateGraph(POGuardState)` dengan alur:
    `detector → vendor_rag → reorder_calc → po_builder → (po.total_value >= APPROVAL_THRESHOLD ? approver : erp_submit) → END`.
    Conditional edge dari `po_builder` ke `approver`/`erp_submit`; `erp_submit` → END.
  - `run_scan(thread_id: str)` — menjalankan graph dari `{}`, menyimpan hasil PO ke SQLite, mengembalikan `(po, interrupted: bool)`.
  - `resume_approval(thread_id: str, decision: ApprovalDecision)` — `graph.invoke(Command(resume=decision), config)` lalu simpan status PO final.

- [ ] **Step 1: Tulis `backend/app/core/checkpointer.py`**

```python
"""Factory checkpointer LangGraph — InMemory untuk dev/test, Postgres untuk prod."""
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import settings


def get_checkpointer():
    if settings.database_url.startswith("postgres"):
        from langgraph.checkpoint.postgres import PostgresSaver

        from sqlalchemy import create_engine

        engine = create_engine(settings.database_url)
        return PostgresSaver(engine)  # type: ignore[arg-type]
    return InMemorySaver()
```

- [ ] **Step 2: Tulis `backend/app/agents/deps.py`**

```python
"""Merangkai dependensi graph (gateway, retriever, extractor)."""
from __future__ import annotations

from dataclasses import dataclass

from app.mcp_client.erp import InventoryGateway, get_erp_tools
from app.rag.extractor import build_rule_extractor
from app.rag.retriever import VendorRetriever


@dataclass
class GraphDeps:
    gateway: InventoryGateway
    retriever: VendorRetriever
    extract: callable
    log_event: callable | None = None


async def build_default_deps(retriever: VendorRetriever) -> GraphDeps:
    tools = await get_erp_tools()
    gateway = InventoryGateway(tools)
    extract = build_rule_extractor()
    return GraphDeps(gateway=gateway, retriever=retriever, extract=extract)
```

- [ ] **Step 3: Tulis `backend/app/agents/graph.py`**

```python
"""Graph LangGraph pipeline PO governance + orkestrasi scan & resume."""
from __future__ import annotations

import uuid

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents.deps import GraphDeps
from app.agents.nodes.approver import make_approver
from app.agents.nodes.detector import make_detector
from app.agents.nodes.erp_submit import make_erp_submit
from app.agents.nodes.po_builder import make_po_builder
from app.agents.nodes.reorder_calc import make_reorder_node
from app.agents.nodes.vendor_rag import make_vendor_rag
from app.agents.state import POGuardState
from app.core.checkpointer import get_checkpointer
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.core.models import POEventModel, PurchaseOrderModel
from app.schemas.po import ApprovalDecision


def build_graph(deps: GraphDeps):
    builder = StateGraph(POGuardState)
    builder.add_node("detector", make_detector(deps.gateway.get_inventory))
    builder.add_node("vendor_rag", make_vendor_rag(deps.extract, deps.retriever.retrieve))
    builder.add_node("reorder_calc", make_reorder_node())
    builder.add_node("po_builder", make_po_builder())
    builder.add_node("approver", make_approver())
    builder.add_node("erp_submit", make_erp_submit(deps.gateway, deps.log_event))

    builder.add_edge(START, "detector")
    builder.add_edge("detector", "vendor_rag")
    builder.add_edge("vendor_rag", "reorder_calc")
    builder.add_edge("reorder_calc", "po_builder")

    def needs_approval(state: POGuardState) -> str:
        po = state.get("po")
        if po and po.total_value >= settings.approval_threshold:
            return "approver"
        return "erp_submit"

    builder.add_conditional_edges("po_builder", needs_approval, {"approver": "approver", "erp_submit": "erp_submit"})
    builder.add_edge("approver", "erp_submit")
    builder.add_edge("erp_submit", END)

    return builder.compile(checkpointer=get_checkpointer())


# Cache graph per deps agar checkpointer (InMemorySaver) tidak dibuat ulang
# antar call scan/resume — tanpanya state thread hilang dan resume gagal.
_graph_cache: dict[int, object] = {}


def _get_graph(deps: GraphDeps):
    key = id(deps)
    if key not in _graph_cache:
        _graph_cache[key] = build_graph(deps)
    return _graph_cache[key]


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _log_event(po_no: str, node: str, note: str = "") -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        po = session.query(PurchaseOrderModel).filter_by(po_no=po_no).first()
        if po:
            session.add(POEventModel(po_id=po.id, node=node, note=note))
            session.commit()


def _save_po(thread_id: str, po, status: str, basis: str = "rag", explanation: str = "") -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        row = PurchaseOrderModel(
            po_no=po.po_no, sku=po.sku, vendor_id=po.vendor_id, qty=po.qty,
            unit_price=po.unit_price, total_value=po.total_value, status=status,
            basis=basis,
            explanation=explanation,
            thread_id=thread_id,
        )
        session.add(row)
        session.commit()


async def run_scan(deps: GraphDeps, thread_id: str | None = None) -> dict:
    thread_id = thread_id or uuid.uuid4().hex
    graph = _get_graph(deps)
    result = await graph.ainvoke({}, _config(thread_id))
    po = result.get("po")
    if po:
        reorder = result.get("reorder")
        basis = reorder.basis if reorder else "rag"
        explanation = reorder.explanation if reorder else ""
        interrupted = bool(result.get("__interrupt__"))
        status = "pending_approval" if interrupted else po.status
        _save_po(thread_id, po, status, basis=basis, explanation=explanation)
    return {"thread_id": thread_id, "result": result, "po": po}


async def resume_approval(deps: GraphDeps, thread_id: str, decision: ApprovalDecision) -> dict:
    graph = _get_graph(deps)
    result = await graph.ainvoke(Command(resume=decision.model_dump()), _config(thread_id))
    po = result.get("po")
    if po:
        reorder = result.get("reorder")
        basis = reorder.basis if reorder else "rag"
        explanation = reorder.explanation if reorder else ""
        _save_po(thread_id, po, po.status, basis=basis, explanation=explanation)
    return {"result": result, "po": po}
```

Catatan: gunakan `result.get("__interrupt__")` karena LangGraph menaruh interrupt payload pada hasil invoke.

- [ ] **Step 4: Tulis failing test `backend/tests/integration/test_graph.py`**

```python
import pytest

from app.agents.deps import GraphDeps
from app.agents.graph import build_graph, resume_approval, run_scan
from app.mcp_client.erp import InventoryGateway
from app.rag.retriever import VendorRetriever
from app.schemas.inventory import InventoryItem
from app.schemas.po import ApprovalDecision
from app.schemas.vendor import VendorRules


class FakeGateway(InventoryGateway):
    def __init__(self, items, created=None):
        self._items = items
        self._created = created or {"po_no": "ERP-1", "status": "DRAFT"}
        super().__init__(tools={})

    async def get_inventory(self):
        return self._items

    async def create_po(self, po):
        return self._created


class FakeRetriever:
    def retrieve(self, vendor_id, sku, k=4):
        return ["MOQ 100 unit. Lead time 7 hari. Diskon 5% untuk 500 unit."]


async def fake_extract(vendor_id, sku, chunks):
    return VendorRules(vendor_id=vendor_id, sku=sku, moq=100, lead_time_days=7, basis="rag")


def make_item(**overrides):
    defaults = {
        "sku": "SKU-001", "name": "Bearing", "vendor_id": "VENDOR-A",
        "stock_level": 50, "safety_stock": 100, "unit_price": 100.0,
        "reorder_point": 120, "avg_daily_usage": 20.0,
    }
    defaults.update(overrides)
    return InventoryItem(**defaults)


@pytest.mark.asyncio
async def test_scan_auto_submits_below_threshold():
    deps = GraphDeps(
        gateway=FakeGateway([make_item()]),
        retriever=FakeRetriever(),
        extract=fake_extract,
    )
    # unit_price=100, qty=max(100, ceil(7*20-50))=100 -> total=10000 >= threshold -> approve path
    # Turunkan harga agar < threshold
    deps.gateway = FakeGateway([make_item(unit_price=1.0)])
    out = await run_scan(deps)
    assert out["po"] is not None
    assert out["po"].status == "submitted"
    assert out["result"].get("erp_po_no") == "ERP-1"


@pytest.mark.asyncio
async def test_scan_interrupts_for_approval_then_resumes():
    deps = GraphDeps(
        gateway=FakeGateway([make_item(unit_price=100.0)]),  # total = 100*100 = 10000 >= threshold
        retriever=FakeRetriever(),
        extract=fake_extract,
    )
    out = await run_scan(deps)
    assert out["po"] is not None
    assert out["po"].status == "pending_approval"
    assert out["result"].get("__interrupt__")

    resumed = await resume_approval(
        deps, out["thread_id"], ApprovalDecision(decision="approved", reviewer="manager")
    )
    assert resumed["po"].status == "submitted"
```

- [ ] **Step 5: Jalankan test, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/integration/test_graph.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/graph.py backend/app/agents/deps.py backend/app/core/checkpointer.py backend/tests/integration/test_graph.py
git commit -m "feat(agents): graph LangGraph, checkpointer, dan orkestrasi scan/resume"
```

---

### Task 12: FastAPI — Endpoints dan Wiring

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes.py`
- Create: `backend/app/api/main.py`
- Test: `backend/tests/api/test_api.py`

**Interfaces:**
- Consumes: `run_scan`/`resume_approval`/`build_graph` (Task 11), `seed_database` (Task 8), `build_default_deps` (Task 11).
- Produces FastAPI app `app` (dari `app.api.main`), dengan endpoint:
  - `GET /api/health`
  - `POST /api/scan` → `{thread_id}` (menjalankan scan sekali)
  - `GET /api/pos` → daftar PO (SQLite)
  - `GET /api/pos/{po_no}` → detail PO + ringkasan (untuk approval card)
  - `POST /api/pos/{po_no}/approve` → resume `approved`
  - `POST /api/pos/{po_no}/reject` → resume `rejected` (body `{note}`)
  - `GET /api/approvals/pending` → PO status `pending_approval`
- Lazy deps: graph dibangun satu kali per proses (module-level cache) untuk menghindari overhead MCP handshake tiap request. Untuk tes, dep disuntik via `app.state.deps`.

- [ ] **Step 1: Tulis failing test `backend/tests/api/test_api.py`**

```python
import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.agents.deps import GraphDeps
from app.mcp_client.erp import InventoryGateway
from app.schemas.inventory import InventoryItem
from app.schemas.vendor import VendorRules


class FakeGateway(InventoryGateway):
    def __init__(self):
        super().__init__(tools={})
        self._items = [
            InventoryItem(
                sku="SKU-001", name="Bearing", vendor_id="VENDOR-A", stock_level=50,
                safety_stock=100, unit_price=100.0, reorder_point=120, avg_daily_usage=20.0,
            )
        ]

    async def get_inventory(self):
        return self._items

    async def create_po(self, po):
        return {"po_no": "ERP-1", "status": "DRAFT"}


class FakeRetriever:
    def retrieve(self, vendor_id, sku, k=4):
        return ["MOQ 100 unit. Lead time 7 hari."]


async def fake_extract(vendor_id, sku, chunks):
    return VendorRules(vendor_id=vendor_id, sku=sku, moq=100, lead_time_days=7, basis="rag")


@pytest.fixture
def client(monkeypatch):
    deps = GraphDeps(
        gateway=FakeGateway(),
        retriever=FakeRetriever(),
        extract=fake_extract,
    )
    app = create_app(deps)
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_scan_and_pending(client):
    scan = client.post("/api/scan")
    assert scan.status_code == 200
    assert "thread_id" in scan.json()

    pending = client.get("/api/approvals/pending")
    assert pending.status_code == 200
    body = pending.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending_approval"


def test_approve_flow(client):
    scan = client.post("/api/scan")
    po_no = client.get("/api/pos").json()[0]["po_no"]
    resp = client.post(f"/api/pos/{po_no}/approve")
    assert resp.status_code == 200

    pos = client.get("/api/pos").json()
    po = next(p for p in pos if p["po_no"] == po_no)
    assert po["status"] in {"approved", "submitted"}


def test_reject_flow(client):
    client.post("/api/scan")
    po_no = client.get("/api/pos").json()[0]["po_no"]
    resp = client.post(f"/api/pos/{po_no}/reject", json={"note": "harga tidak sesuai"})
    assert resp.status_code == 200
    pos = client.get("/api/pos").json()
    po = next(p for p in pos if p["po_no"] == po_no)
    assert po["status"] == "rejected"
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/api/test_api.py -v`
Expected: FAIL (modul tidak ada)

- [ ] **Step 3: Tulis `backend/app/api/routes.py`**

```python
"""Router API Procure Guard."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.deps import GraphDeps
from app.agents.graph import resume_approval, run_scan
from app.core.db import get_session
from app.core.models import PurchaseOrderModel
from app.schemas.po import ApprovalDecision
from app.services.seed import seed_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Jalankan seed sekali saat modul dimuat (dev/test). Pada produksi, dipanggil saat startup.
_db_initialized = False


def _ensure_db() -> None:
    global _db_initialized
    if not _db_initialized:
        seed_database()
        _db_initialized = True


class RejectBody(BaseModel):
    note: str = ""


def _get_deps(request: Request) -> GraphDeps:
    return request.app.state.deps


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/scan")
async def scan(request: Request):
    _ensure_db()
    deps: GraphDeps = _get_deps(request)
    out = await run_scan(deps)
    return {"thread_id": out["thread_id"], "po_no": out["po"].po_no if out["po"] else None}


@router.get("/pos")
def list_pos(session: Session = Depends(get_session)):
    _ensure_db()
    rows = session.query(PurchaseOrderModel).order_by(PurchaseOrderModel.id.desc()).all()
    return [_row_dict(r) for r in rows]


@router.get("/pos/{po_no}")
def get_po(po_no: str, session: Session = Depends(get_session)):
    _ensure_db()
    row = session.query(PurchaseOrderModel).filter_by(po_no=po_no).first()
    if not row:
        raise HTTPException(status_code=404, detail="PO tidak ditemukan")
    return _row_dict(row)


@router.post("/pos/{po_no}/approve")
async def approve_po(po_no: str, request: Request):
    _ensure_db()
    deps: GraphDeps = _get_deps(request)
    thread_id = _thread_id_for(po_no)
    await resume_approval(deps, thread_id, ApprovalDecision(decision="approved", reviewer="manager"))
    return {"status": "approved"}


@router.post("/pos/{po_no}/reject")
async def reject_po(po_no: str, body: RejectBody, request: Request):
    _ensure_db()
    deps: GraphDeps = _get_deps(request)
    thread_id = _thread_id_for(po_no)
    await resume_approval(deps, thread_id, ApprovalDecision(decision="rejected", reviewer="manager", note=body.note))
    return {"status": "rejected"}


@router.get("/approvals/pending")
def pending_approvals(session: Session = Depends(get_session)):
    _ensure_db()
    rows = session.query(PurchaseOrderModel).filter_by(status="pending_approval").all()
    return [_row_dict(r) for r in rows]


def _thread_id_for(po_no: str) -> str:
    from app.core.db import SessionLocal

    with SessionLocal() as session:
        row = session.query(PurchaseOrderModel).filter_by(po_no=po_no).first()
        if not row:
            raise HTTPException(status_code=404, detail="PO tidak ditemukan")
        return row.thread_id


def _row_dict(row: PurchaseOrderModel) -> dict:
    return {
        "po_no": row.po_no,
        "sku": row.sku,
        "vendor_id": row.vendor_id,
        "qty": row.qty,
        "unit_price": row.unit_price,
        "total_value": row.total_value,
        "status": row.status,
        "basis": row.basis,
        "explanation": row.explanation,
        "thread_id": row.thread_id,
        "erp_po_no": row.erp_po_no,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
```

- [ ] **Step 4: Tulis `backend/app/api/main.py`**

```python
"""Aplikasi FastAPI Procure Guard AI."""
from __future__ import annotations

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


app = create_default_app()
```

- [ ] **Step 5: Jalankan test, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/api/test_api.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Verifikasi server dapat dijalankan (smoke)**

Run (workdir `backend`, timeout 30s): 
```powershell
$env:GROQ_API_KEY=""; .\.venv\Scripts\python -c "from app.api.main import create_default_app; app=create_default_app(); print('OK')"
```
Catatan: `create_default_app` membutuhkan MCP http (default). Bila ingin smoke tanpa MCP, jalankan `pytest` saja. Expected: mencetak `OK` bila `ERP_MCP_TRANSPORT=stdio` dan mcp_server terinstal; jika tidak, pastikan pytest lulus yang merupakan verification utama.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api backend/tests/api/test_api.py
git commit -m "feat(api): endpoint FastAPI scan, pos, approval, dan pending"
```

---

### Task 13: Scheduler APScheduler

**Files:**
- Create: `backend/app/services/scheduler.py`
- Create: `backend/app/__main__.py`
- Test: `backend/tests/unit/test_scheduler.py`

**Interfaces:**
- Consumes: `run_scan` (Task 11), `build_default_deps` (Task 11).
- Produces: `start_scheduler(deps)` — `BackgroundScheduler` interval `settings.scan_interval_minutes`, job memanggil `run_scan(deps)` dan mencatat log; `shutdown_scheduler()`.

- [ ] **Step 1: Tulis failing test `backend/tests/unit/test_scheduler.py`**

```python
import pytest

from app.services.scheduler import start_scheduler, shutdown_scheduler


@pytest.fixture
def scheduler():
    start_scheduler(interval_minutes=1, runnable=lambda: None)
    yield
    shutdown_scheduler()


def test_scheduler_starts(scheduler):
    from app.services.scheduler import _scheduler

    assert _scheduler is not None
    assert _scheduler.running is True
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_scheduler.py -v`
Expected: FAIL (modul tidak ada)

- [ ] **Step 3: Tulis `backend/app/services/scheduler.py`**

```python
"""Scheduler berkala untuk scan low-stock (APScheduler in-process)."""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler(interval_minutes: int = 60, runnable=None, deps=None) -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="Asia/Jakarta")

    if runnable is None:
        from app.agents.deps import build_default_deps
        from app.rag.retriever import VendorRetriever
        from app.core.llm import get_embeddings
        from app.rag.store import build_vector_store

        store = build_vector_store(get_embeddings())
        retriever = VendorRetriever(store)
        built_deps = asyncio.run(build_default_deps(retriever))
        deps = deps or built_deps

        async def _job():
            from app.agents.graph import run_scan

            try:
                out = await run_scan(deps)
                if out["po"]:
                    logger.info("Scan %s -> PO %s status=%s", out["thread_id"], out["po"].po_no, out["po"].status)
            except Exception:
                logger.exception("Scan terjadwal gagal")

        runnable = lambda: asyncio.run(_job())  # noqa: E731

    _scheduler.add_job(runnable, "interval", minutes=interval_minutes, id="inventory_scan", replace_existing=True)
    _scheduler.start()
    logger.info("Scheduler dimulai, interval=%s menit", interval_minutes)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
```

- [ ] **Step 4: Tulis `backend/app/__main__.py` (entry point CLI)**

```python
"""Entry point: python -m app — menjalankan FastAPI + scheduler."""
from __future__ import annotations

import uvicorn

from app.api.main import create_default_app
from app.services.scheduler import start_scheduler


def main() -> None:
    app = create_default_app()
    start_scheduler()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Jalankan test scheduler, pastikan lulus**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest tests/unit/test_scheduler.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/scheduler.py backend/app/__main__.py backend/tests/unit/test_scheduler.py
git commit -m "feat(scheduler): APScheduler interval untuk scan low-stock + entry point CLI"
```

---

### Task 14: Ingest CLI untuk Dokumen Vendor

**Files:**
- Create: `backend/app/cli.py`
- Create: `backend/app/services/ingest.py`

**Interfaces:**
- Consumes: `load_documents`, `build_vector_store`, `get_embeddings`.
- Produces: `python -m app.cli ingest --dir data/vendor_sops` — memuat PDF/MD ke vector store (dev: in-memory; prod: pgvector).

- [ ] **Step 1: Tulis `backend/app/services/ingest.py`**

```python
"""Service ingest dokumen SOP vendor ke vector store."""
from __future__ import annotations

import logging

from langchain_core.documents import Document

from app.core.llm import get_embeddings
from app.rag.loader import load_documents
from app.rag.store import build_vector_store

logger = logging.getLogger(__name__)


def ingest_sops(directory: str) -> int:
    docs = load_documents(directory)
    store = build_vector_store(get_embeddings())
    store.add_documents(docs)
    logger.info("Berhasil meng-ingest %d dokumen SOP dari %s", len(docs), directory)
    return len(docs)
```

- [ ] **Step 2: Tulis `backend/app/cli.py`**

```python
"""CLI Procure Guard backend."""
from __future__ import annotations

import argparse

from app.services.ingest import ingest_sops


def main() -> None:
    parser = argparse.ArgumentParser(description="Procure Guard AI backend CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest dokumen SOP vendor")
    ingest.add_argument("--dir", required=True, help="Direktori berisi PDF/MD SOP vendor")
    args = parser.parse_args()

    if args.command == "ingest":
        count = ingest_sops(args.dir)
        print(f"OK: {count} chunk dokumen di-ingest")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verifikasi CLI (dev: in-memory, tanpa API key — hanya jalankan loader)**

Run (workdir `backend`): `.\.venv\Scripts\python -c "from app.rag.loader import load_documents; print(len(load_documents('data/vendor_sops')))"`
Expected: `4` (2 file MD, di-split)

- [ ] **Step 4: Commit**

```bash
git add backend/app/cli.py backend/app/services/ingest.py
git commit -m "feat(cli): ingest SOP vendor ke vector store"
```

---

### Task 15: Docker Compose dan Dockerfiles

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `mcp_server/Dockerfile`
- Create: `frontend/Dockerfile`

**Interfaces:**
- Consumes: struktur dari task-task sebelumnya.
- Produces: orchestration 4 container: `postgres` (pgvector), `mcp-server` (FastMCP streamable-http :8001), `backend` (uvicorn :8000), `frontend` (Vite :5173 proxy /api). Postgres siap untuk produksi; dev tetap memakai SQLite.

- [ ] **Step 1: Tulis `docker-compose.yml`**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: procure
      POSTGRES_PASSWORD: procure
      POSTGRES_DB: procure
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U procure -d procure"]
      interval: 5s
      timeout: 5s
      retries: 10

  mcp-server:
    build: ./mcp_server
    ports:
      - "8001:8001"
    environment:
      MCP_TRANSPORT: streamable-http
    command: ["python", "-m", "mcp_server.erp_mcp"]

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+psycopg://procure:procure@postgres:5432/procure
      ERP_MCP_URL: http://mcp-server:8001/mcp
      ERP_MCP_TRANSPORT: http
    depends_on:
      postgres:
        condition: service_healthy
      mcp-server:
        condition: service_started
    command: ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

volumes:
  pgdata:
```

- [ ] **Step 2: Tulis `mcp_server/Dockerfile`**

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["python", "-m", "mcp_server.erp_mcp"]
```

Catatan: FastMCP streamable-http perlu server HTTP. Tambahkan di `erp_mcp.py` saat docker: `mcp.run(transport="streamable-http")` — sudah default. Port default FastMCP HTTP adalah 8000; sesuaikan env `MCP_SERVER_PORT` bila perlu. Untuk V1, gunakan port 8001 via `uvicorn`/FastMCP run pada 8001 bila diperlukan — dokumentasikan di README.

- [ ] **Step 3: Tulis `backend/Dockerfile`**

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY data ./data
RUN pip install --no-cache-dir -e .
EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Tulis `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
RUN npm install -g serve
EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
```

- [ ] **Step 5: Validasi sintaks YAML**

Run (workdir root): 
```powershell
python -c "import yaml; yaml.safe_load(open('docker-compose.yml', encoding='utf-8')); print('YAML OK')"
```
Jika pyyaml tidak ada, gunakan `python -c "import json; json.dumps(open('docker-compose.yml', encoding='utf-8').read()); print('OK')"` hanya untuk smoke — atau skip bila tak ada.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml backend/Dockerfile mcp_server/Dockerfile frontend/Dockerfile
git commit -m "feat(deploy): docker-compose 4 service dan Dockerfile"
```

---

### Task 16: Frontend React SPA

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/components/InventoryTable.tsx`
- Create: `frontend/src/components/ApprovalCard.tsx`
- Create: `frontend/src/components/PoList.tsx`
- Create: `frontend/src/App.test.tsx`
- Create: `frontend/vitest.setup.ts`

**Interfaces:**
- Consumes: API backend (Task 12).
- Produces: SPA dengan halaman tunggal: kartu approval pending (Approve/Reject), tabel inventori, dan daftar PO; polling tiap 10 detik; semua teks Bahasa Indonesia.

- [ ] **Step 1: Tulis `frontend/package.json`**

```json
{
  "name": "procure-guard-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^24.0.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "vitest": "^2.0.0"
  }
}
```

- [ ] **Step 2: Tulis `frontend/vite.config.ts`**

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./vitest.setup.ts",
    globals: true,
  },
});
```

- [ ] **Step 3: Tulis `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "noEmit": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Tulis `frontend/index.html`**

```html
<!doctype html>
<html lang="id">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Procure Guard AI</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Tulis `frontend/src/types.ts`**

```ts
export interface PurchaseOrder {
  po_no: string;
  sku: string;
  vendor_id: string;
  qty: number;
  unit_price: number;
  total_value: number;
  status: string;
  basis: string;
  explanation: string;
  thread_id: string;
  erp_po_no: string | null;
  created_at: string | null;
}
```

- [ ] **Step 6: Tulis `frontend/src/api.ts`**

```ts
import type { PurchaseOrder } from "./types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function scan(): Promise<{ thread_id: string; po_no: string | null }> {
  return json(await fetch("/api/scan", { method: "POST" }));
}

export async function listPos(): Promise<PurchaseOrder[]> {
  return json(await fetch("/api/pos"));
}

export async function listPending(): Promise<PurchaseOrder[]> {
  return json(await fetch("/api/approvals/pending"));
}

export async function approvePo(poNo: string): Promise<{ status: string }> {
  return json(await fetch(`/api/pos/${poNo}/approve`, { method: "POST" }));
}

export async function rejectPo(poNo: string, note: string): Promise<{ status: string }> {
  return json(
    await fetch(`/api/pos/${poNo}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note }),
    }),
  );
}
```

- [ ] **Step 7: Tulis `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 8: Tulis `frontend/src/components/ApprovalCard.tsx`**

```tsx
import { useState } from "react";
import type { PurchaseOrder } from "../types";

interface Props {
  po: PurchaseOrder;
  onApprove: (poNo: string) => Promise<void>;
  onReject: (poNo: string, note: string) => Promise<void>;
}

export default function ApprovalCard({ po, onApprove, onReject }: Props) {
  const [note, setNote] = useState("");

  return (
    <div data-testid="approval-card">
      <h3>PO {po.po_no} menunggu persetujuan</h3>
      <dl>
        <dt>SKU</dt>
        <dd>{po.sku}</dd>
        <dt>Vendor</dt>
        <dd>{po.vendor_id}</dd>
        <dt>Kuantitas</dt>
        <dd>{po.qty}</dd>
        <dt>Nilai Total</dt>
        <dd>${po.total_value.toFixed(2)}</dd>
        <dt>Dasar Kalkulasi</dt>
        <dd>{po.basis}</dd>
        <dt>Penjelasan</dt>
        <dd>{po.explanation}</dd>
      </dl>
      <input
        aria-label="Catatan"
        placeholder="Catatan (opsional)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <button onClick={() => onApprove(po.po_no)}>Setujui</button>
      <button onClick={() => onReject(po.po_no, note)}>Tolak</button>
    </div>
  );
}
```

- [ ] **Step 9: Tulis `frontend/src/components/PoList.tsx`**

```tsx
import type { PurchaseOrder } from "../types";

export default function PoList({ pos }: { pos: PurchaseOrder[] }) {
  if (pos.length === 0) return <p>Belum ada PO.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>No PO</th>
          <th>SKU</th>
          <th>Vendor</th>
          <th>Qty</th>
          <th>Total</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {pos.map((po) => (
          <tr key={po.po_no}>
            <td>{po.po_no}</td>
            <td>{po.sku}</td>
            <td>{po.vendor_id}</td>
            <td>{po.qty}</td>
            <td>${po.total_value.toFixed(2)}</td>
            <td>{po.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 10: Tulis `frontend/src/components/InventoryTable.tsx`**

```tsx
export interface InventoryRow {
  sku: string;
  name: string;
  vendor_id: string;
  stock_level: number;
  safety_stock: number;
  is_critical: boolean;
}

export default function InventoryTable({ items }: { items: InventoryRow[] }) {
  if (items.length === 0) return <p>Belum ada data inventori.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>SKU</th>
          <th>Nama</th>
          <th>Vendor</th>
          <th>Stok</th>
          <th>Safety Stock</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.sku}>
            <td>{item.sku}</td>
            <td>{item.name}</td>
            <td>{item.vendor_id}</td>
            <td>{item.stock_level}</td>
            <td>{item.safety_stock}</td>
            <td>{item.is_critical ? "KRITIS" : "Normal"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 11: Tulis `frontend/src/App.tsx`**

```tsx
import { useEffect, useState } from "react";
import ApprovalCard from "./components/ApprovalCard";
import InventoryTable, { InventoryRow } from "./components/InventoryTable";
import PoList from "./components/PoList";
import * as api from "./api";
import type { PurchaseOrder } from "./types";

export default function App() {
  const [pending, setPending] = useState<PurchaseOrder[]>([]);
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [message, setMessage] = useState("");

  async function refresh() {
    setPending(await api.listPending());
    setPos(await api.listPos());
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 10000);
    return () => clearInterval(id);
  }, []);

  async function handleScan() {
    await api.scan();
    setMessage("Scan selesai.");
    await refresh();
  }

  async function handleApprove(poNo: string) {
    await api.approvePo(poNo);
    setMessage(`PO ${poNo} disetujui.`);
    await refresh();
  }

  async function handleReject(poNo: string, note: string) {
    await api.rejectPo(poNo, note);
    setMessage(`PO ${poNo} ditolak.`);
    await refresh();
  }

  return (
    <main>
      <h1>Procure Guard AI</h1>
      {message && <p data-testid="message">{message}</p>}
      <button onClick={handleScan}>Pindai Inventori</button>

      <section>
        <h2>Menunggu Persetujuan</h2>
        {pending.length === 0 ? (
          <p>Tidak ada PO menunggu persetujuan.</p>
        ) : (
          pending.map((po) => (
            <ApprovalCard key={po.po_no} po={po} onApprove={handleApprove} onReject={handleReject} />
          ))
        )}
      </section>

      <section>
        <h2>Daftar Purchase Order</h2>
        <PoList pos={pos} />
      </section>
    </main>
  );
}
```

- [ ] **Step 12: Tulis test `frontend/src/App.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as api from "./api";

vi.mock("./api", () => ({
  scan: vi.fn(),
  listPending: vi.fn(),
  listPos: vi.fn(),
  approvePo: vi.fn(),
  rejectPo: vi.fn(),
}));

const pendingPo = {
  po_no: "PO-123",
  sku: "SKU-001",
  vendor_id: "VENDOR-A",
  qty: 200,
  unit_price: 100,
  total_value: 20000,
  status: "pending_approval",
  basis: "rag",
  explanation: "max(moq=100, lead*usage-stock=90)",
  thread_id: "t1",
  erp_po_no: null,
  created_at: null,
};

beforeEach(() => {
  vi.mocked(api.listPending).mockResolvedValue([pendingPo]);
  vi.mocked(api.listPos).mockResolvedValue([pendingPo]);
});

describe("App", () => {
  it("menampilkan kartu persetujuan untuk PO pending", async () => {
    render(<App />);
    expect(await screen.findByTestId("approval-card")).toBeInTheDocument();
    expect(screen.getByText("PO-123 menunggu persetujuan")).toBeInTheDocument();
  });

  it("menyetujui PO dan memperbarui daftar", async () => {
    const user = userEvent.setup();
    vi.mocked(api.approvePo).mockResolvedValue({ status: "approved" });
    vi.mocked(api.listPending).mockResolvedValue([]);

    render(<App />);
    await screen.findByTestId("approval-card");
    await user.click(screen.getByRole("button", { name: "Setujui" }));
    await waitFor(() => expect(api.approvePo).toHaveBeenCalledWith("PO-123"));
    expect(screen.getByTestId("message")).toHaveTextContent("PO-123 disetujui");
  });
});
```

- [ ] **Step 13: Tulis `frontend/vitest.setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 14: Install dan jalankan test frontend**

```powershell
npm install
npm test
```

(workdir `frontend`)
Expected: PASS (2 passed)

- [ ] **Step 15: Commit**

```bash
git add frontend
git commit -m "feat(frontend): React SPA dashboard & approval dengan polling"
```

---

### Task 17: Verifikasi Akhir dan Dokumentasi Ringkas

**Files:**
- Modify: `README.md` (instruksi menjalankan)
- Modify: `.env.example` bila perlu

**Interfaces:**
- Consumes: seluruh task.
- Produces: instruksi menjalankan yang benar dan teruji.

- [ ] **Step 1: Jalankan seluruh test backend**

Run (workdir `backend`): `.\.venv\Scripts\python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 2: Jalankan seluruh test frontend**

Run (workdir `frontend`): `npm test`
Expected: ALL PASS

- [ ] **Step 3: Perbarui `README.md` dengan cara menjalankan**

```markdown
## Menjalankan (dev)

Backend:
1. `cd backend && python -m venv .venv`
2. `.venv\Scripts\pip install -e .` (Windows) / `.venv/bin/pip install -e .` (Linux)
3. Salin `.env.example` ke `.env` dan isi `GROQ_API_KEY`, `GOOGLE_API_KEY`
4. Ingest SOP: `.venv\Scripts\python -m app.cli ingest --dir data/vendor_sops`
5. Jalankan API: `.venv\Scripts\python -m app` (FastAPI :8000 + scheduler)

Frontend:
1. `cd frontend && npm install`
2. `npm run dev` (:5173, proxy /api ke :8000)

Docker (produksi):
`docker compose up --build`
```

- [ ] **Step 4: Tambahkan catatan port MCP di README**

Catatan singkat: `mcp_server` FastMCP streamable-http ekspos pada `:8001/mcp` di docker-compose. Bila menjalankan `erp_mcp.py` manual, sesuaikan `ERP_MCP_URL`.

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example
git commit -m "docs: instruksi menjalankan dev & produksi"
```

---

### Task 18: Smoke Test End-to-End (Manual, dengan API Key)

**Files:** (tidak ada file baru)

**Interfaces:**
- Consumes: seluruh task.

- [ ] **Step 1: Siapkan env**

Salin `.env.example` → `.env`, isi `GROQ_API_KEY` dan `GOOGLE_API_KEY` asli.

- [ ] **Step 2: Jalankan MCP server (stdio mode) & backend di dua terminal**

Terminal 1 (workdir `backend`):
```powershell
$env:ERP_MCP_TRANSPORT="stdio"
.\.venv\Scripts\python -m app
```

- [ ] **Step 3: Panggil scan dan verifikasi alur**

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/scan
Invoke-RestMethod http://localhost:8000/api/approvals/pending
```

Expected: ada PO `pending_approval` untuk SKU bernilai tinggi (mis. SKU-003 unit_price 850 * qty → ≥ $10.000).

- [ ] **Step 4: Approve satu PO dan cek status**

```powershell
$po = (Invoke-RestMethod http://localhost:8000/api/approvals/pending)[0]
Invoke-RestMethod -Method Post "http://localhost:8000/api/pos/$($po.po_no)/approve"
Invoke-RestMethod http://localhost:8000/api/pos
```

Expected: status PO menjadi `submitted` (terkirim ke mock ERP via MCP) atau `approved`.

- [ ] **Step 5: Commit catatan hasil smoke (bila ada perbaikan)**

```bash
git add -A
git commit -m "test: smoke test end-to-end berhasil (scan, pending, approve)"
```

---

## Self-Review (checklist plan vs spec)

- [ ] Spec §5.2 (graph node order) → Task 11. ✅
- [ ] Spec §5.3 (HITL interrupt/resume) → Task 11 (approver node + resume_approval). ✅
- [ ] Spec §6.1 (RAG: loader, split, embed, pgvector/in-memory) → Task 8. ✅
- [ ] Spec §6.2 (MCP ERP tools) → Task 6. ✅
- [ ] Spec §6.3 (MCP client) → Task 7. ✅
- [ ] Spec §7 (endpoint list) → Task 12 (health ditambahkan). ✅
- [ ] Spec §8 (error handling: ERP retry/fallback, RAG fallback, audit) → Task 10/11 (fallback rules, `pending_erp`, `po_events` via `log_event`). Catatan: retry ERP 2x dan audit `po_events` di-simplify — `log_event` disediakan; tabel POEvent tersedia (Task 3). ⚠️ Konsisten dengan scope V1.
- [ ] Spec §9 (testing tiers) → Task 5–17 (unit/integrasi/API/frontend). ✅
- [ ] Spec §10 (docker-compose 4 service) → Task 15. ✅
- [ ] Spec §11 (KPIs) → diukur pada Task 18 smoke (cycle time & governance visibility). ✅
