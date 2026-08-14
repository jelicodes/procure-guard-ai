import asyncio
import json
import sys
from pathlib import Path

import pytest
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from mcp_server.mock_erp.database import reset_database, seed_inventory

SAMPLE_INVENTORY = [
    {
        "sku": "SKU-001", "name": "Bearing 6204", "vendor_id": "VENDOR-A",
        "stock_level": 50, "safety_stock": 100, "unit_price": 12.5,
        "reorder_point": 120, "avg_daily_usage": 20.0,
    }
]

REPO_ROOT = str(Path(__file__).resolve().parents[3])

# Konfigurasi server stdio: interpreter venv yang sedang berjalan (sys.executable),
# cwd repo root agar `python -m mcp_server.erp_mcp` dapat mengimpor modul, serta
# seed inventori via env ERP_SEED_INVENTORY karena proses anak stdio berjalan
# dengan memori (modul mock_erp) yang terpisah dari proses induk.
MCP_SERVER_CONFIG = {
    "transport": "stdio",
    "command": sys.executable,
    "args": ["-m", "mcp_server.erp_mcp"],
    "cwd": REPO_ROOT,
    "env": {
        "MCP_TRANSPORT": "stdio",
        "ERP_SEED_INVENTORY": json.dumps(SAMPLE_INVENTORY),
    },
}


def _parsing_payload(result) -> list | dict:
    """Ambil payload JSON dari blok teks hasil panggilan tool MCP."""
    blok = result[0] if isinstance(result, list) else result
    return json.loads(blok["text"])


@pytest.fixture(autouse=True)
def _clean_db():
    reset_database()
    seed_inventory(SAMPLE_INVENTORY)
    yield
    reset_database()


@pytest.mark.asyncio
async def test_mcp_get_inventory_tool():
    client = MultiServerMCPClient({"erp": MCP_SERVER_CONFIG})
    async with client.session("erp") as session:
        tools = {t.name: t for t in await load_mcp_tools(session)}
        assert "get_inventory" in tools

        result = await tools["get_inventory"].ainvoke({})
        assert _parsing_payload(result)[0]["sku"] == "SKU-001"


@pytest.mark.asyncio
async def test_mcp_create_po_roundtrip():
    client = MultiServerMCPClient({"erp": MCP_SERVER_CONFIG})
    async with client.session("erp") as session:
        tools = {t.name: t for t in await load_mcp_tools(session)}
        created = await tools["create_po"].ainvoke(
            {"po": {"po_no": "PO-100", "sku": "SKU-001", "vendor_id": "VENDOR-A", "qty": 200, "unit_price": 12.5, "total_value": 2500.0}}
        )
        assert _parsing_payload(created)["status"] == "DRAFT"
        status = await tools["get_po_status"].ainvoke({"po_no": "PO-100"})
        assert _parsing_payload(status)["po_no"] == "PO-100"