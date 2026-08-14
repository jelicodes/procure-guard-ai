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
    # base = ceil(7*20 - 50) = 90 -> tier 500 di luar batas 90*1.5=135? TIDAK -> tetap 90
    assert result.reorder_qty == 90


def test_reorder_uses_tier_when_base_close():
    rules = VendorRules(
        vendor_id="VENDOR-A", moq=0, lead_time_days=7,
        discount_tiers=[DiscountTier(min_qty=100, discount_pct=5.0)],
    )
    result = compute_reorder(make_item(), rules)
    # base=90, tier 100 ada di [90, 135] -> 100
    assert result.reorder_qty == 100


def test_reorder_minimum_positive_when_stock_above_need():
    rules = VendorRules(vendor_id="VENDOR-A", moq=50, lead_time_days=7)
    item = make_item(stock=300, usage=10.0)  # base = 7*10-300 < 0
    result = compute_reorder(item, rules)
    assert result.reorder_qty == 50