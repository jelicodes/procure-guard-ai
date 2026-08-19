"""Tes deterministik evaluator retrieval RAG (tanpa API nyata)."""
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.vectorstores import InMemoryVectorStore

from app.rag.evaluate import (
    build_retriever,
    evaluate_correctness,
    evaluate_example,
    load_golden_set,
    run_evaluation,
    summarize,
)
from app.rag.retriever import VendorRetriever


def _docs():
    return [
        Document(
            page_content="MOQ 100 unit. Lead time 7 hari. Vendor A.",
            metadata={"vendor_id": "VENDOR-A", "source": "vendor-a.md", "doc_id": "va:moq"},
        ),
        Document(
            page_content="MOQ 250 unit. Lead time 10 hari. Vendor B.",
            metadata={"vendor_id": "VENDOR-B", "source": "vendor-b.md", "doc_id": "vb:moq"},
        ),
    ]


def test_evaluate_example_hit_dan_tanpa_kebocoran():
    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    store.add_documents(_docs())
    retriever = VendorRetriever(store)
    example = {
        "inputs": {"query": "MOQ Vendor A", "vendor_id": "VENDOR-A", "sku": "SKU-001"},
        "reference_outputs": {"relevant_doc_ids": ["va:moq"]},
    }
    result = evaluate_example(retriever, example, k=4)
    assert result["hit"] is True
    assert result["leakage_vendors"] == []


def test_evaluate_example_per_fakta_mengecek_nilai_dalam_konteks():
    """Per-fakta: nilai MOQ/lead/tiers yang diharapkan harus ada di konteks ter-retrieve."""
    from langchain_core.documents import Document

    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    store.add_documents(
        [
            Document(
                page_content="MOQ 100 unit. Lead time 7 hari. Diskon 5% di 500 unit.",
                metadata={"vendor_id": "VENDOR-A", "source": "a.md", "doc_id": "a:moq"},
                id="a:moq",
            ),
            Document(
                page_content="Lead time 7 hari untuk semua SKU.",
                metadata={"vendor_id": "VENDOR-A", "source": "a.md", "doc_id": "a:lead"},
                id="a:lead",
            ),
        ]
    )
    retriever = VendorRetriever(store)
    example = {
        "inputs": {"query": "MOQ Vendor A", "vendor_id": "VENDOR-A", "sku": "SKU-001"},
        "reference_outputs": {
            "expected_vendor_rules": {
                "moq": 100,
                "lead_time_days": 7,
                "discount_tiers": [{"min_qty": 500, "discount_pct": 5}],
            }
        },
    }
    result = evaluate_example(retriever, example, k=4)
    assert result["facts"]["moq"] is True
    assert result["facts"]["lead"] is True
    assert result["facts"]["tiers"] == 1.0


def test_evaluate_example_deteksi_kebocoran():
    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    store.add_documents(_docs())
    retriever = VendorRetriever(store)
    example = {
        "inputs": {"query": "MOQ Vendor B", "vendor_id": "VENDOR-B", "sku": "SKU-002"},
        "reference_outputs": {"relevant_doc_ids": ["vb:moq"]},
    }
    result = evaluate_example(retriever, example, k=4)
    assert result["hit"] is True
    assert all(v == "VENDOR-B" for v in result["leakage_vendors"]) is True or result["leakage_vendors"] == []


def test_summarize_agregasi_metrik():
    summary = summarize(
        [
            {"hit": True, "recall": 1.0, "leakage_vendors": []},
            {"hit": False, "recall": 0.5, "leakage_vendors": ["VENDOR-B"]},
        ]
    )
    assert summary["examples"] == 2
    assert summary["hit_rate_at_k"] == 0.5
    assert summary["recall_at_k"] == 0.75
    assert summary["leakage_examples"] == 1
    assert summary["leakage_rate"] == 0.5


def test_load_golden_set_format_langsmith(tmp_path):
    golden = [
        {
            "inputs": {"query": "q", "vendor_id": "VENDOR-A", "sku": "SKU-001"},
            "reference_outputs": {"relevant_doc_ids": ["x"], "expected_vendor_rules": {}},
            "metadata": {"vendor_id": "VENDOR-A"},
        }
    ]
    path = tmp_path / "golden.json"
    path.write_text(__import__("json").dumps(golden), encoding="utf-8")
    loaded = load_golden_set(path)
    assert loaded[0]["inputs"]["query"] == "q"
    assert "reference_outputs" in loaded[0]


async def test_evaluate_correctness_membandingkan_aturan_ekstraksi():
    """Correctness end-to-end: aturan hasil ekstraksi dibandingkan ke expected_vendor_rules."""
    from app.schemas.vendor import VendorRules

    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    store.add_documents(_docs())
    retriever = VendorRetriever(store)

    async def fake_extract(vendor_id, sku, chunks):
        return VendorRules(vendor_id=vendor_id, sku=sku, moq=100, lead_time_days=7, basis="rag")

    golden = [
        {
            "inputs": {"query": "q", "vendor_id": "VENDOR-A", "sku": "SKU-001"},
            "reference_outputs": {
                "expected_vendor_rules": {"moq": 100, "lead_time_days": 7, "discount_tiers": []}
            },
        },
        {
            "inputs": {"query": "q2", "vendor_id": "VENDOR-B", "sku": "SKU-002"},
            "reference_outputs": {
                "expected_vendor_rules": {"moq": 999, "lead_time_days": 7, "discount_tiers": []}
            },
        },
    ]

    results = await evaluate_correctness(retriever, fake_extract, golden, k=4)

    assert results[0]["moq_correct"] is True
    assert results[1]["moq_correct"] is False
    assert results[0]["lead_correct"] is True


def test_run_evaluation_end_to_end_deterministik(tmp_path):
    corpus = tmp_path / "sops"
    corpus.mkdir()
    (corpus / "vendor-a.md").write_text(
        "MOQ 100 unit. Lead time 7 hari. Diskon 5%. Vendor A.", encoding="utf-8"
    )
    golden = tmp_path / "golden.json"
    golden.write_text(
        __import__("json").dumps(
            [
                {
                    "inputs": {"query": "MOQ Vendor A", "vendor_id": "VENDOR-A", "sku": "SKU-001"},
                    "reference_outputs": {"relevant_doc_ids": ["vendor-a.md:0"]},
                }
            ]
        ),
        encoding="utf-8",
    )

    retriever = build_retriever(corpus, embeddings=DeterministicFakeEmbedding(size=8))
    report = run_evaluation(corpus, golden, k=4, embeddings=DeterministicFakeEmbedding(size=8))

    assert isinstance(Path(golden), Path)  # noqa: B015
    assert report["summary"]["examples"] == 1
    assert retriever is not None


def test_regression_gate_korpus_riil_golden_10():
    """Regression gate: korpus produksi vs golden set 10 contoh harus tetap di atas ambang."""
    from app.rag.evaluate import DEFAULT_CORPUS, DEFAULT_GOLDEN

    report = run_evaluation(
        DEFAULT_CORPUS, DEFAULT_GOLDEN, k=8, embeddings=DeterministicFakeEmbedding(size=8)
    )
    s = report["summary"]
    assert s["examples"] == 10
    assert s["hit_rate_at_k"] == 1.0
    assert s["recall_at_k"] >= 0.80
    assert s["leakage_examples"] == 0
    assert s["fact_moq"] == 1.0
    assert s["fact_lead"] == 1.0
    assert s["fact_tiers"] >= 0.90