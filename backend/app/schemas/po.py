from typing import Literal

from pydantic import BaseModel, Field


class ReorderCalc(BaseModel):
    sku: str
    reorder_qty: int = Field(gt=0)
    total_value: float
    explanation: str
    basis: str = "rag"


class PurchaseOrder(BaseModel):
    po_no: str
    sku: str
    vendor_id: str
    qty: int = Field(gt=0)
    unit_price: float
    total_value: float
    status: str = "draft"
    line_items: list[dict] = Field(default_factory=list)
    created_at: str | None = None


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewer: str = "manager"
    note: str = ""