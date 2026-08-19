from langchain_core.documents import Document

from app.rag.extractor import build_rule_extractor
from app.schemas.vendor import VendorRules


class FakeStructuredModel:
    """Mengembalikan VendorRules tanpa benar-benar memanggil LLM."""

    def __init__(self, result: VendorRules):
        self._result = result
        self.last_prompt = None
        self.last_schema = None

    def with_structured_output(self, schema):
        self.last_schema = schema
        return self

    async def ainvoke(self, prompt: str) -> VendorRules:
        self.last_prompt = prompt
        return self._result


async def test_extractor_schema_tidak_memuat_sources():
    """Field sources di-set deterministik di sisi Python; skema tool LLM harus bebas
    dari field opsional tersebut agar Groq tidak gagal validasi saat LLM kirim null."""
    expected = VendorRules(vendor_id="VENDOR-A", sku="SKU-001", moq=100, basis="rag")
    model = FakeStructuredModel(expected)
    extract = build_rule_extractor(model=model)
    chunk = Document(page_content="MOQ 100 unit", metadata={"source": "vendor-a.md"})
    await extract("VENDOR-A", "SKU-001", [chunk])

    schema = model.last_schema.model_json_schema()
    assert "sources" not in schema["properties"], "sources tidak boleh menjadi properti skema"
    assert "vendor_id" in schema["properties"]
    assert "moq" in schema["properties"]


async def test_extractor_returns_structured_rules():
    expected = VendorRules(vendor_id="VENDOR-A", sku="SKU-001", moq=100, lead_time_days=7, basis="rag")
    model = FakeStructuredModel(expected)
    extract = build_rule_extractor(model=model)
    chunk = Document(page_content="MOQ 100 unit, lead time 7 hari", metadata={"source": "vendor-a.md"})
    rules = await extract("VENDOR-A", "SKU-001", [chunk])
    assert rules.moq == 100
    assert rules.basis == "rag"


async def test_extractor_mengisi_sources_dari_metadata_chunk():
    expected = VendorRules(vendor_id="VENDOR-A", sku="SKU-001", moq=100, lead_time_days=7, basis="rag")
    model = FakeStructuredModel(expected)
    extract = build_rule_extractor(model=model)
    chunks = [
        Document(page_content="MOQ 100 unit", metadata={"source": "vendor-a.md"}),
        Document(page_content="Lead time 7 hari", metadata={"source": "vendor-a.md"}),
    ]
    rules = await extract("VENDOR-A", "SKU-001", chunks)
    assert rules.sources == ["vendor-a.md"]


async def test_extractor_prompt_mengutamakan_sku_spesifik():
    expected = VendorRules(vendor_id="VENDOR-A", sku="SKU-001", moq=100, lead_time_days=7, basis="rag")
    model = FakeStructuredModel(expected)
    extract = build_rule_extractor(model=model)
    chunk = Document(page_content="Ketentuan SKU-003: MOQ 5 unit", metadata={"source": "vendor-a.md"})
    await extract("VENDOR-A", "SKU-003", [chunk])
    assert "SKU-003" in model.last_prompt
    assert "khusus" in model.last_prompt.lower() or "prioritas" in model.last_prompt.lower()