import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.agents.deps import GraphDeps
from app.core.db import Base, SessionLocal, engine
from app.core.models import POEventModel, PurchaseOrderModel
from app.mcp_client.erp import InventoryGateway
from app.schemas.inventory import InventoryItem
from app.schemas.vendor import VendorRules


class FakeGateway(InventoryGateway):
    def __init__(self):
        super().__init__(tools={})
        self._items = [
            InventoryItem(
                sku="SKU-001", name="Bearing", vendor_id="VENDOR-A", stock_level=50,
                safety_stock=100, unit_price=500_000.0, reorder_point=120, avg_daily_usage=20.0,
            )
        ]

    async def get_inventory(self):
        return self._items

    async def create_po(self, po):
        return {"po_no": "ERP-1", "status": "DRAFT"}


class FakeRetriever:
    def retrieve(self, vendor_id, sku, k=4):
        return ["MOQ 100 unit. Lead time 7 hari."]


async def fake_extract(vendor_id, sku, chunks):
    return VendorRules(vendor_id=vendor_id, sku=sku, moq=100, lead_time_days=7, basis="rag")


@pytest.fixture
def client(monkeypatch):
    deps = GraphDeps(
        gateway=FakeGateway(),
        retriever=FakeRetriever(),
        extract=fake_extract,
    )
    app = create_app(deps)
    # Bersihkan PO sisa dari sesi/tes sebelumnya agar hitungan pending deterministik.
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        session.query(POEventModel).delete()
        session.query(PurchaseOrderModel).delete()
        session.commit()
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_scan_and_pending(client):
    scan = client.post("/api/scan")
    assert scan.status_code == 200
    assert "thread_id" in scan.json()

    pending = client.get("/api/approvals/pending")
    assert pending.status_code == 200
    body = pending.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending_approval"


def test_approve_flow(client):
    scan = client.post("/api/scan")
    po_no = client.get("/api/pos").json()[0]["po_no"]
    resp = client.post(f"/api/pos/{po_no}/approve")
    assert resp.status_code == 200

    pos = client.get("/api/pos").json()
    po = next(p for p in pos if p["po_no"] == po_no)
    assert po["status"] in {"approved", "submitted"}


def test_reject_flow(client):
    client.post("/api/scan")
    po_no = client.get("/api/pos").json()[0]["po_no"]
    resp = client.post(f"/api/pos/{po_no}/reject", json={"note": "harga tidak sesuai"})
    assert resp.status_code == 200
    pos = client.get("/api/pos").json()
    po = next(p for p in pos if p["po_no"] == po_no)
    assert po["status"] == "rejected"