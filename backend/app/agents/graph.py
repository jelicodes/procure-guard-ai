"""Graph LangGraph pipeline PO governance + orkestrasi scan & resume."""
from __future__ import annotations

import uuid

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents.deps import GraphDeps
from app.agents.nodes.approver import make_approver
from app.agents.nodes.detector import make_detector
from app.agents.nodes.erp_submit import make_erp_submit
from app.agents.nodes.po_builder import make_po_builder
from app.agents.nodes.reorder_calc import make_reorder_node
from app.agents.nodes.vendor_rag import make_vendor_rag
from app.agents.state import POGuardState
from app.core.checkpointer import get_checkpointer
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.core.models import POEventModel, PurchaseOrderModel
from app.schemas.po import ApprovalDecision


def build_graph(deps: GraphDeps):
    builder = StateGraph(POGuardState)
    builder.add_node("detector", make_detector(deps.gateway.get_inventory))
    builder.add_node("vendor_rag", make_vendor_rag(deps.extract, deps.retriever.retrieve))
    builder.add_node("reorder_calc", make_reorder_node())
    builder.add_node("po_builder", make_po_builder())
    builder.add_node("approver", make_approver())
    builder.add_node("erp_submit", make_erp_submit(deps.gateway, deps.log_event))

    builder.add_edge(START, "detector")
    builder.add_edge("detector", "vendor_rag")
    builder.add_edge("vendor_rag", "reorder_calc")
    builder.add_edge("reorder_calc", "po_builder")

    def needs_approval(state: POGuardState) -> str:
        po = state.get("po")
        if po and po.total_value >= settings.approval_threshold:
            return "approver"
        return "erp_submit"

    builder.add_conditional_edges("po_builder", needs_approval, {"approver": "approver", "erp_submit": "erp_submit"})
    builder.add_edge("approver", "erp_submit")
    builder.add_edge("erp_submit", END)

    return builder.compile(checkpointer=get_checkpointer())


# Cache graph per deps agar checkpointer (InMemorySaver) tidak dibuat ulang
# antar call scan/resume — tanpanya state thread hilang dan resume gagal.
# Simpan referensi deps agar id(deps) tidak dipakai ulang oleh objek lain
# selama graph masih dicache (mencegah salah ambil graph antar deps).
_graph_cache: dict[int, tuple[object, object]] = {}


def _get_graph(deps: GraphDeps):
    key = id(deps)
    if key not in _graph_cache:
        _graph_cache[key] = (deps, build_graph(deps))
    return _graph_cache[key][1]


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _log_event(po_no: str, node: str, note: str = "") -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        po = session.query(PurchaseOrderModel).filter_by(po_no=po_no).first()
        if po:
            session.add(POEventModel(po_id=po.id, node=node, note=note))
            session.commit()


def _save_po(thread_id: str, po, status: str, basis: str = "rag", explanation: str = "") -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        row = session.query(PurchaseOrderModel).filter_by(po_no=po.po_no).first()
        if row is None:
            row = PurchaseOrderModel(po_no=po.po_no)
            session.add(row)
        row.sku = po.sku
        row.vendor_id = po.vendor_id
        row.qty = po.qty
        row.unit_price = po.unit_price
        row.total_value = po.total_value
        row.status = status
        row.basis = basis
        row.explanation = explanation
        row.thread_id = thread_id
        session.commit()


async def run_scan(deps: GraphDeps, thread_id: str | None = None) -> dict:
    thread_id = thread_id or uuid.uuid4().hex
    graph = _get_graph(deps)
    result = await graph.ainvoke({}, _config(thread_id))
    po = result.get("po")
    if po:
        reorder = result.get("reorder")
        basis = reorder.basis if reorder else "rag"
        explanation = reorder.explanation if reorder else ""
        interrupted = bool(result.get("__interrupt__"))
        status = "pending_approval" if interrupted else po.status
        po.status = status
        _save_po(thread_id, po, status, basis=basis, explanation=explanation)
    return {"thread_id": thread_id, "result": result, "po": po}


async def resume_approval(deps: GraphDeps, thread_id: str, decision: ApprovalDecision) -> dict:
    graph = _get_graph(deps)
    result = await graph.ainvoke(Command(resume=decision.model_dump()), _config(thread_id))
    po = result.get("po")
    if po:
        reorder = result.get("reorder")
        basis = reorder.basis if reorder else "rag"
        explanation = reorder.explanation if reorder else ""
        _save_po(thread_id, po, po.status, basis=basis, explanation=explanation)
    return {"result": result, "po": po}