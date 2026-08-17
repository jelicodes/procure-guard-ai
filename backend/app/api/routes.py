"""Router API Procure Guard."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.deps import GraphDeps
from app.agents.graph import log_event, resume_approval, run_scan
from app.core.db import get_session
from app.core.models import InventoryItemModel, POEventModel, PurchaseOrderModel
from app.schemas.po import ApprovalDecision
from app.services.seed import seed_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Jalankan seed sekali saat modul dimuat (dev/test). Pada produksi, dipanggil saat startup.
_db_initialized = False


def _ensure_db() -> None:
    global _db_initialized
    if not _db_initialized:
        seed_database()
        _db_initialized = True


class RejectBody(BaseModel):
    note: str = ""


class ApproveBody(BaseModel):
    reviewer: str = "manager"
    note: str = ""


def _get_deps(request: Request) -> GraphDeps:
    return request.app.state.deps


def _ensure_deps_logging(deps: GraphDeps) -> None:
    if deps.log_event is None:
        deps.log_event = log_event


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/inventory")
def list_inventory(session: Session = Depends(get_session)):
    _ensure_db()
    rows = session.query(InventoryItemModel).all()
    return [
        {
            "sku": r.sku,
            "name": r.name,
            "vendor_id": r.vendor_id,
            "stock_level": r.stock_level,
            "safety_stock": r.safety_stock,
            "unit_price": r.unit_price,
            "reorder_point": r.reorder_point,
            "avg_daily_usage": r.avg_daily_usage,
        }
        for r in rows
    ]


@router.get("/events")
def list_events(session: Session = Depends(get_session)):
    _ensure_db()
    rows = (
        session.query(POEventModel, PurchaseOrderModel.po_no)
        .join(PurchaseOrderModel, POEventModel.po_id == PurchaseOrderModel.id)
        .order_by(POEventModel.id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": ev.id,
            "po_no": po_no,
            "timestamp": ev.created_at.isoformat() if ev.created_at else None,
            "node": ev.node,
            "actor": ev.actor,
            "note": ev.note,
        }
        for ev, po_no in rows
    ]


@router.post("/scan")
async def scan(request: Request):
    _ensure_db()
    deps: GraphDeps = _get_deps(request)
    _ensure_deps_logging(deps)
    out = await run_scan(deps)
    po = out["po"]
    if po is None:
        log_event("", "detector", "Tidak ada stok kritis — scan selesai tanpa PO.")
    else:
        log_event(po.po_no, "detector", f"Stok kritis terdeteksi: {po.sku}")
        log_event(po.po_no, "vendor_rag", f"Aturan vendor {po.vendor_id} dimuat.")
        log_event(po.po_no, "reorder_calc", out["result"].get("reorder").explanation if out["result"].get("reorder") else "Kalkulasi reorder selesai.")
        if po.status == "pending_approval":
            log_event(po.po_no, "po_builder", "PO dibangun dan menunggu persetujuan manusia.")
        else:
            log_event(po.po_no, "erp_submit", f"PO dikirim ke ERP: {out['result'].get('erp_po_no')}")
    return {"thread_id": out["thread_id"], "po_no": po.po_no if po else None}


@router.get("/pos")
def list_pos(session: Session = Depends(get_session)):
    _ensure_db()
    rows = session.query(PurchaseOrderModel).order_by(PurchaseOrderModel.id.desc()).all()
    return [_row_dict(r) for r in rows]


@router.get("/pos/{po_no}")
def get_po(po_no: str, session: Session = Depends(get_session)):
    _ensure_db()
    row = session.query(PurchaseOrderModel).filter_by(po_no=po_no).first()
    if not row:
        raise HTTPException(status_code=404, detail="PO tidak ditemukan")
    return _row_dict(row)


@router.post("/pos/{po_no}/approve")
async def approve_po(po_no: str, body: ApproveBody | None = None, request: Request = None):
    _ensure_db()
    deps: GraphDeps = _get_deps(request)
    _ensure_deps_logging(deps)
    body = body or ApproveBody()
    thread_id = _thread_id_for(po_no)
    await resume_approval(deps, thread_id, ApprovalDecision(decision="approved", reviewer=body.reviewer, note=body.note))
    log_event(po_no, "human_governance", f"Disetujui oleh {body.reviewer}: {body.note}")
    return {"status": "approved"}


@router.post("/pos/{po_no}/reject")
async def reject_po(po_no: str, body: RejectBody, request: Request):
    _ensure_db()
    deps: GraphDeps = _get_deps(request)
    _ensure_deps_logging(deps)
    thread_id = _thread_id_for(po_no)
    await resume_approval(deps, thread_id, ApprovalDecision(decision="rejected", reviewer="manager", note=body.note))
    log_event(po_no, "human_governance", f"Ditolak: {body.note}")
    return {"status": "rejected"}


@router.get("/approvals/pending")
def pending_approvals(session: Session = Depends(get_session)):
    _ensure_db()
    rows = session.query(PurchaseOrderModel).filter_by(status="pending_approval").all()
    return [_row_dict(r) for r in rows]


def _thread_id_for(po_no: str) -> str:
    from app.core.db import SessionLocal

    with SessionLocal() as session:
        row = session.query(PurchaseOrderModel).filter_by(po_no=po_no).first()
        if not row:
            raise HTTPException(status_code=404, detail="PO tidak ditemukan")
        return row.thread_id


def _row_dict(row: PurchaseOrderModel) -> dict:
    return {
        "po_no": row.po_no,
        "sku": row.sku,
        "vendor_id": row.vendor_id,
        "qty": row.qty,
        "unit_price": row.unit_price,
        "total_value": row.total_value,
        "status": row.status,
        "basis": row.basis,
        "explanation": row.explanation,
        "thread_id": row.thread_id,
        "erp_po_no": row.erp_po_no,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }