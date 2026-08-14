"""State typed untuk LangGraph pipeline PO governance."""
from typing import TypedDict

from app.schemas.inventory import InventoryItem
from app.schemas.po import ApprovalDecision, PurchaseOrder, ReorderCalc
from app.schemas.vendor import VendorRules


class POGuardState(TypedDict, total=False):
    inventory: InventoryItem
    vendor_rules: VendorRules
    reorder: ReorderCalc
    po: PurchaseOrder
    approval: ApprovalDecision
    erp_po_no: str
    error: str