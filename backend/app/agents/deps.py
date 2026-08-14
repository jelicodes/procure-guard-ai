"""Merangkai dependensi graph (gateway, retriever, extractor)."""
from __future__ import annotations

from dataclasses import dataclass

from app.mcp_client.erp import InventoryGateway, get_erp_tools
from app.rag.extractor import build_rule_extractor
from app.rag.retriever import VendorRetriever


@dataclass
class GraphDeps:
    gateway: InventoryGateway
    retriever: VendorRetriever
    extract: callable
    log_event: callable | None = None


async def build_default_deps(retriever: VendorRetriever) -> GraphDeps:
    tools = await get_erp_tools()
    gateway = InventoryGateway(tools)
    extract = build_rule_extractor()
    return GraphDeps(gateway=gateway, retriever=retriever, extract=extract)