"""Node approval human-in-the-loop — interrupt() lalu resume dengan keputusan."""
from __future__ import annotations

from pydantic import ValidationError
from langgraph.types import interrupt

from app.schemas.po import ApprovalDecision


def make_approver():
    async def approver(state):
        po = state["po"]
        payload = {
            "type": "approval_request",
            "po_no": po.po_no,
            "sku": po.sku,
            "vendor_id": po.vendor_id,
            "qty": po.qty,
            "total_value": po.total_value,
            "explanation": state["reorder"].explanation,
            "basis": state["reorder"].basis,
        }
        decision = interrupt(payload)
        try:
            approval = ApprovalDecision(**decision)
        except ValidationError:
            approval = ApprovalDecision(decision="rejected", reviewer="system", note="Payload resume tidak valid")
        if approval.decision == "approved":
            po.status = "approved"
        else:
            po.status = "rejected"
        return {"approval": approval, "po": po}

    return approver