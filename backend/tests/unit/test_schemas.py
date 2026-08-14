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