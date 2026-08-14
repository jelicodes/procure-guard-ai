import json

import pytest

from app.mcp_client.erp import InventoryGateway
from app.schemas.inventory import InventoryItem
from app.schemas.po import PurchaseOrder


class FakeTool:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, args):
        return self._result


@pytest.mark.asyncio
async def test_gateway_get_inventory_maps_items():
    tools = {
        "get_inventory": FakeTool([{"sku": "SKU-001", "name": "Bearing", "vendor_id": "VENDOR-A", "stock_level": 50, "safety_stock": 100, "unit_price": 12.5, "reorder_point": 120, "avg_daily_usage": 20.0}]),
    }
    gw = InventoryGateway(tools)
    items = await gw.get_inventory()
    assert items[0].sku == "SKU-001"
    assert items[0].is_critical is True


@pytest.mark.asyncio
async def test_gateway_create_po():
    tools = {"create_po": FakeTool({"po_no": "PO-1", "status": "DRAFT"})}
    gw = InventoryGateway(tools)
    po = PurchaseOrder(po_no="PO-1", sku="SKU-001", vendor_id="VENDOR-A", qty=200, unit_price=12.5, total_value=2500.0)
    result = await gw.create_po(po)
    assert result["status"] == "DRAFT"


def _tool_result_content_block(payload):
    return [{"type": "text", "text": json.dumps(payload)}]


@pytest.mark.asyncio
async def test_gateway_get_inventory_menangani_content_blocks():
    tools = {
        "get_inventory": FakeTool(
            _tool_result_content_block([{"sku": "SKU-001", "name": "Bearing", "vendor_id": "VENDOR-A", "stock_level": 50, "safety_stock": 100, "unit_price": 12.5, "reorder_point": 120, "avg_daily_usage": 20.0}])
        ),
    }
    gw = InventoryGateway(tools)
    items = await gw.get_inventory()
    assert items[0].sku == "SKU-001"
    assert items[0].is_critical is True


@pytest.mark.asyncio
async def test_gateway_create_po_menangani_content_blocks():
    tools = {"create_po": FakeTool(_tool_result_content_block({"po_no": "PO-1", "status": "DRAFT"}))}
    gw = InventoryGateway(tools)
    po = PurchaseOrder(po_no="PO-1", sku="SKU-001", vendor_id="VENDOR-A", qty=200, unit_price=12.5, total_value=2500.0)
    result = await gw.create_po(po)
    assert result["status"] == "DRAFT"
