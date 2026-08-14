"""Node kalkulasi reorder quantity."""
from __future__ import annotations

from app.services.reorder import compute_reorder


def make_reorder_node():
    async def reorder_calc(state):
        reorder = compute_reorder(state["inventory"], state["vendor_rules"])
        return {"reorder": reorder}

    return reorder_calc