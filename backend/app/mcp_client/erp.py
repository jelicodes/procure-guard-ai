"""Klien MCP ke ERP — membungkus MultiServerMCPClient agar node graph mudah dipakai."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import settings
from app.schemas.inventory import InventoryItem
from app.schemas.po import PurchaseOrder

REPO_ROOT = str(Path(__file__).resolve().parents[3])

SEED_FILE = Path(REPO_ROOT) / "backend" / "data" / "inventory_seed.json"


def _load_seed_inventory() -> str:
    """Baca seed inventori bawaan sebagai JSON string untuk proses anak stdio.

    Proses anak ERP stdio berjalan dengan memori (modul mock_erp) yang terpisah,
    sehingga inventori harus disuntikkan lewat env ERP_SEED_INVENTORY.
    """
    return SEED_FILE.read_text(encoding="utf-8")


def _unwrap_content(result: Any) -> Any:
    """Ambil payload dari content blocks hasil panggilan tool MCP.

    Adaptor MCP membungkus hasil tool dalam content blocks teks berupa JSON,
    misalnya ``[{"type": "text", "text": "<json>"}]``. Tool fiktif di unit test
    mengembalikan objek biasa (dict/list) dan dikembalikan apa adanya.
    """
    if isinstance(result, list):
        teks = [b.get("text") for b in result if isinstance(b, dict) and b.get("type") == "text"]
        if teks:
            return json.loads("".join(teks))
        return result
    if isinstance(result, dict) and result.get("type") == "text" and "text" in result:
        return json.loads(result["text"])
    return result


async def get_erp_tools() -> dict[str, BaseTool]:
    if settings.erp_mcp_transport == "stdio":
        servers = {
            "erp": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "mcp_server.erp_mcp"],
                "cwd": REPO_ROOT,
                "env": {
                    "MCP_TRANSPORT": "stdio",
                    "ERP_SEED_INVENTORY": _load_seed_inventory(),
                },
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
        raw = _unwrap_content(await self._tools["get_inventory"].ainvoke({}))
        return [InventoryItem(**item) for item in raw]

    async def create_po(self, po: PurchaseOrder) -> dict:
        raw = _unwrap_content(await self._tools["create_po"].ainvoke({"po": po.model_dump()}))
        return raw
