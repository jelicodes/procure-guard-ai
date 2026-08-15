import pytest

from app.agents.deps import GraphDeps
from app.agents.graph import build_graph, resume_approval, run_scan
from app.core.db import SessionLocal
from app.core.models import PurchaseOrderModel
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
    # unit_price=100, qty=max(100, ceil(7*20-50))=100 -> total=10000 >= ambang -> jalur persetujuan
    # Turunkan harga agar < ambang (threshold)
    deps.gateway = FakeGateway([make_item(unit_price=1.0)])
    out = await run_scan(deps)
    assert out["po"] is not None
    assert out["po"].status == "submitted"
    assert out["result"].get("erp_po_no") == "ERP-1"

    # erp_po_no harus ter-persist ke DB agar API /api/pos menampilkannya.
    with SessionLocal() as session:
        row = session.query(PurchaseOrderModel).filter_by(po_no=out["po"].po_no).first()
        assert row is not None
        assert row.erp_po_no == "ERP-1"


@pytest.mark.asyncio
async def test_scan_no_critical_stock_returns_without_error():
    # Semua item sehat (bukan kritis) -> scan harus selesai tanpa error/500 dan po None.
    deps = GraphDeps(
        gateway=FakeGateway([make_item(stock_level=500, safety_stock=100)]),
        retriever=FakeRetriever(),
        extract=fake_extract,
    )
    out = await run_scan(deps)
    assert out["po"] is None
    assert out["result"].get("error") == "no_critical_stock"


@pytest.mark.asyncio
async def test_scan_interrupts_for_approval_then_resumes():
    deps = GraphDeps(
        gateway=FakeGateway([make_item(unit_price=100.0)]),  # total = 100*100 = 10000 >= ambang
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