"""MCP server ERP — membungkus mock Oracle ERP menjadi MCP tools."""
from __future__ import annotations

import json
import os
from datetime import datetime

from fastmcp import FastMCP

from mcp_server.mock_erp.database import seed_inventory
from mcp_server.mock_erp.operations import (
    check_po_status,
    create_po as create_erp_po,
    list_inventory,
)

mcp = FastMCP("erp")


def _seed_inventory_dari_env() -> None:
    """Isi inventori mock dari env ERP_SEED_INVENTORY (JSON) untuk proses anak stdio."""
    raw = os.environ.get("ERP_SEED_INVENTORY")
    if raw:
        seed_inventory(json.loads(raw))


_seed_inventory_dari_env()


@mcp.tool()
def get_inventory() -> list[dict]:
    """Mengembalikan daftar level inventori terkini dari ERP."""
    return list_inventory()


@mcp.tool()
def create_po(po: dict) -> dict:
    """Membuat Purchase Order baru di ERP dan mengembalikan nomor PO.

    Args:
        po: dict dengan kunci po_no, sku, vendor_id, qty, unit_price, total_value.
    """
    return create_erp_po(po)


@mcp.tool()
def get_po_status(po_no: str) -> dict:
    """Mengembalikan status Purchase Order berdasarkan nomor PO."""
    return check_po_status(po_no)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    if transport == "stdio":
        mcp.run(transport=transport)
    else:
        # Bind 0.0.0.0:8001 agar dapat dijangkau backend di dalam docker-compose
        # (default FastMCP hanya 127.0.0.1:8000).
        mcp.run(transport=transport, host="0.0.0.0", port=8001)