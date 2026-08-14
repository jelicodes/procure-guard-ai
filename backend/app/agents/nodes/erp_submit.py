"""Node submit PO ke ERP via MCP gateway."""
from __future__ import annotations

from app.mcp_client.erp import InventoryGateway


def make_erp_submit(gateway: InventoryGateway, log_event: callable | None = None):
    async def erp_submit(state):
        po = state["po"]
        if state.get("approval") and state["approval"].decision == "rejected":
            return {"po": po}
        try:
            result = await gateway.create_po(po)
            po.status = "submitted"
            return {"erp_po_no": result.get("po_no"), "po": po}
        except Exception as exc:
            po.status = "pending_erp"
            if log_event:
                log_event(po.po_no, "erp_submit", f"ERP gagal: {exc}")
            return {"error": str(exc), "po": po}

    return erp_submit