from pydantic import BaseModel, Field


class DiscountTier(BaseModel):
    min_qty: int = Field(gt=0)
    discount_pct: float = Field(ge=0, le=100)


class PenaltyClause(BaseModel):
    condition: str
    penalty: str


class VendorRules(BaseModel):
    vendor_id: str
    sku: str | None = None
    moq: int = 0
    lead_time_days: int = 7
    discount_tiers: list[DiscountTier] = Field(default_factory=list)
    penalty_clauses: list[PenaltyClause] = Field(default_factory=list)
    min_order_value: float = 0.0
    basis: str = "rag"