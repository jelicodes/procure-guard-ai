from pydantic import BaseModel


class InventoryItem(BaseModel):
    sku: str
    name: str
    vendor_id: str
    stock_level: int
    safety_stock: int
    unit_price: float
    reorder_point: int
    avg_daily_usage: float

    @property
    def is_critical(self) -> bool:
        return self.stock_level <= self.safety_stock