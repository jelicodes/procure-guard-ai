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