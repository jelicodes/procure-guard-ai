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