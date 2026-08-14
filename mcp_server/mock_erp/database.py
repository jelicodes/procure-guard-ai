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