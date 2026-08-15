"""Ekstraksi aturan vendor dari chunk SOP via structured output LLM."""
from __future__ import annotations

from app.schemas.vendor import VendorRules


def build_rule_extractor(model=None):
    """Membangun fungsi extract. `model` dapat di-inject untuk tes."""
    if model is None:
        from app.core.llm import get_chat_model

        model = get_chat_model()

    structured = model.with_structured_output(VendorRules)

    async def extract(vendor_id: str, sku: str, chunks: list[str]) -> VendorRules:
        prompt = (
            f"Ekstrak aturan pengadaan untuk vendor {vendor_id} (SKU {sku}) dari "
            f"ekstrak SOP berikut. Jika suatu field tidak ada, gunakan nilai default "
            f"(moq=0, lead_time_days=7). Selalu set basis='rag'.\n\n"
            f"Ekstrak SOP:\n" + "\n---\n".join(chunks)
        )
        return await structured.ainvoke(prompt)

    return extract