"""Router API Procure Guard."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.deps import GraphDeps
from app.agents.graph import resume_approval, run_scan
from app.core.db import get_session
from app.core.models import PurchaseOrderModel
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


def _get_deps(request: Request) -> GraphDeps:
    return request.app.state.deps


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/scan")
async def scan(request: Request):
    _ensure_db()
    deps: GraphDeps = _get_deps(request)
    out = await run_scan(deps)
    return {"thread_id": out["thread_id"], "po_no": out["po"].po_no if out["po"] else None}


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
async def approve_po(po_no: str, request: Request):
    _ensure_db()
    deps: GraphDeps = _get_deps(request)
    thread_id = _thread_id_for(po_no)
    await resume_approval(deps, thread_id, ApprovalDecision(decision="approved", reviewer="manager"))
    return {"status": "approved"}


@router.post("/pos/{po_no}/reject")
async def reject_po(po_no: str, body: RejectBody, request: Request):
    _ensure_db()
    deps: GraphDeps = _get_deps(request)
    thread_id = _thread_id_for(po_no)
    await resume_approval(deps, thread_id, ApprovalDecision(decision="rejected", reviewer="manager", note=body.note))
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