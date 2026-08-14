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
