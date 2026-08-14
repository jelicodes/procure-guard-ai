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