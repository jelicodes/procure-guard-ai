from app.rag.extractor import build_rule_extractor
from app.schemas.vendor import VendorRules


class FakeStructuredModel:
    """Mengembalikan VendorRules tanpa benar-benar memanggil LLM."""

    def __init__(self, result: VendorRules):
        self._result = result

    def with_structured_output(self, schema):
        return self

    async def ainvoke(self, prompt: str) -> VendorRules:
        return self._result


async def test_extractor_returns_structured_rules():
    expected = VendorRules(vendor_id="VENDOR-A", sku="SKU-001", moq=100, lead_time_days=7, basis="rag")
    extract = build_rule_extractor(model=FakeStructuredModel(expected))
    rules = await extract("VENDOR-A", "SKU-001", ["MOQ 100 unit, lead time 7 hari"])
    assert rules.moq == 100
    assert rules.basis == "rag"