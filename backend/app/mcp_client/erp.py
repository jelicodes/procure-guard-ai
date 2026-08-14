"""Klien MCP ke ERP — membungkus MultiServerMCPClient agar node graph mudah dipakai."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import settings
from app.schemas.inventory import InventoryItem
from app.schemas.po import PurchaseOrder


async def get_erp_tools() -> dict[str, BaseTool]:
    if settings.erp_mcp_transport == "stdio":
        servers = {
            "erp": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "mcp_server.erp_mcp"],
                "env": {"MCP_TRANSPORT": "stdio"},
            }
        }
    else:
        servers = {"erp": {"transport": "http", "url": settings.erp_mcp_url}}

    client = MultiServerMCPClient(servers)
    tools = await client.get_tools()
    return {t.name: t for t in tools}


class InventoryGateway:
    """Gateway ke ERP via MCP tools. Tools dapat di-inject untuk tes."""

    def __init__(self, tools: dict[str, BaseTool | Any]):
        self._tools = tools

    async def get_inventory(self) -> list[InventoryItem]:
        raw = await self._tools["get_inventory"].ainvoke({})
        return [InventoryItem(**item) for item in raw]

    async def create_po(self, po: PurchaseOrder) -> dict:
        return await self._tools["create_po"].ainvoke({"po": po.model_dump()})
