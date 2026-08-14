from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InventoryItemModel(Base):
    __tablename__ = "inventory_items"

    sku: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    vendor_id: Mapped[str] = mapped_column(String, index=True)
    stock_level: Mapped[int] = mapped_column(Integer)
    safety_stock: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    reorder_point: Mapped[int] = mapped_column(Integer)
    avg_daily_usage: Mapped[float] = mapped_column(Float)


class PurchaseOrderModel(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_no: Mapped[str] = mapped_column(String, unique=True)
    sku: Mapped[str] = mapped_column(String, index=True)
    vendor_id: Mapped[str] = mapped_column(String)
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    total_value: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="draft")
    basis: Mapped[str] = mapped_column(String, default="rag")
    explanation: Mapped[str] = mapped_column(Text, default="")
    thread_id: Mapped[str] = mapped_column(String, unique=True)
    erp_po_no: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class POEventModel(Base):
    __tablename__ = "po_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_id: Mapped[int] = mapped_column(Integer, index=True)
    node: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String, default="system")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)