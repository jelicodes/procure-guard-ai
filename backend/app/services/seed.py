"""Seed data inventori contoh ke database (dev/test)."""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.db import Base, SessionLocal, engine
from app.core.models import InventoryItemModel


def seed_database() -> None:
    Base.metadata.create_all(engine)
    seed_path = Path(__file__).resolve().parents[2] / "data" / "inventory_seed.json"
    items = json.loads(seed_path.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        session.query(InventoryItemModel).delete()
        for item in items:
            session.add(InventoryItemModel(**item))
        session.commit()