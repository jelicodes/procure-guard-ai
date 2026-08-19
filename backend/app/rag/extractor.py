"""Ekstraksi aturan vendor dari chunk SOP via structured output LLM."""
from __future__ import annotations

from langchain_core.documents import Document

from app.schemas.vendor import VendorRules, VendorRulesExtract


def build_rule_extractor(model=None):
    """Membangun fungsi extract. `model` dapat di-inject untuk tes."""
    if model is None:
        from app.core.llm import get_chat_model

        model = get_chat_model()

    # Skema LLM sengaja tanpa field `sources` (di-set deterministik di Python)
    # agar Groq tidak menolak tool call saat field opsional diisi null.
    structured = model.with_structured_output(VendorRulesExtract)

    async def extract(vendor_id: str, sku: str, chunks: list[Document]) -> VendorRules:
        sources = sorted({doc.metadata.get("source", "") for doc in chunks if doc.metadata.get("source")})
        prompt = (
            f"Ekstrak aturan pengadaan untuk vendor {vendor_id} dari ekstrak SOP berikut.\n"
            f"Prioritas: (1) ketentuan khusus SKU {sku} lebih diutamakan daripada aturan umum, "
            f"(2) aturan umum hanya dipakai bila ketentuan SKU tidak tersedia.\n"
            f"Jika suatu field tidak ada, gunakan nilai default (moq=0, lead_time_days=7). "
            f"Selalu set basis='rag'.\n\n"
            f"Ekstrak SOP:\n" + "\n---\n".join(doc.page_content for doc in chunks)
        )
        extracted = await structured.ainvoke(prompt)
        rules = VendorRules(**extracted.model_dump())
        rules.sources = sources
        return rules

    return extract