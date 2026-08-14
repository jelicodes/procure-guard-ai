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