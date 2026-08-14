import asyncio

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
        import app.agents.nodes.approver as mod

        mod.interrupt = FakeInterrupt(ApprovalDecision(decision="approved").model_dump())
        return await node(state)

    result = asyncio.run(run())
    assert captured["payload"]["type"] == "approval_request"
    assert result["approval"].decision == "approved"
    assert result["po"].status == "approved"
