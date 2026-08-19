"""Evaluasi deterministik kualitas retrieval RAG terhadap golden set.

Mode `deterministic` (default): hanya mengukur retrieval tanpa memanggil LLM
  — hit-rate@k, recall@k, dan deteksi kebocoran antar-vendor. Aman dijalankan
  dalam tes (tanpa API key) bila store dibangun dari embeddings deterministik.
Mode `llm`: tambahan skor ekstraksi `VendorRules` terhadap reference
  (meniru evaluator correctness LangSmith) — butuh API key.

Format golden set mengikuti skema dataset LangSmith:
  {"inputs": {...}, "reference_outputs": {...}, "metadata": {...}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.vectorstores import InMemoryVectorStore

from app.core.config import settings
from app.rag.retriever import VendorRetriever
from app.rag.store import build_vector_store

DEFAULT_GOLDEN = Path(__file__).resolve().parents[2] / "data" / "golden" / "retrieval-golden.json"
DEFAULT_CORPUS = Path(__file__).resolve().parents[2] / "data" / "vendor_sops"


def load_golden_set(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _retrieved_doc_ids(docs) -> set[str]:
    return {d.metadata.get("doc_id", "") for d in docs}


def _fact_check(expected_rules: dict, docs) -> dict:
    """Per-fakta: cek nilai yang diharapkan muncul dalam konteks ter-retrieve."""
    content = " ".join(d.page_content for d in docs).lower()
    facts = {"moq": False, "lead": False, "tiers": 0.0}
    if not expected_rules:
        return facts
    if "moq" in expected_rules and expected_rules["moq"]:
        facts["moq"] = f"moq {expected_rules['moq']}" in content or f"{expected_rules['moq']} unit" in content
    if "lead_time_days" in expected_rules and expected_rules["lead_time_days"]:
        facts["lead"] = (
            f"lead time {expected_rules['lead_time_days']}" in content
            or f"{expected_rules['lead_time_days']} hari" in content
        )
    tiers = expected_rules.get("discount_tiers") or []
    if tiers:
        found = sum(
            1
            for t in tiers
            if f"diskon {t['discount_pct']}%" in content and f"{t['min_qty']}" in content
        )
        facts["tiers"] = found / len(tiers)
    return facts


def evaluate_example(retriever, example: dict, k: int) -> dict:
    inputs = example["inputs"]
    ref = example["reference_outputs"]
    relevant = set(ref.get("relevant_doc_ids", []))
    docs = retriever.retrieve(inputs["vendor_id"], inputs["sku"], k=k)
    retrieved = _retrieved_doc_ids(docs)
    hit = bool(retrieved & relevant)
    recall = len(retrieved & relevant) / len(relevant) if relevant else 0.0
    leakage = [
        d.metadata.get("vendor_id")
        for d in docs
        if d.metadata.get("vendor_id") != inputs["vendor_id"]
    ]
    return {
        "query": inputs["query"],
        "vendor_id": inputs["vendor_id"],
        "hit": hit,
        "recall": recall,
        "facts": _fact_check(ref.get("expected_vendor_rules") or {}, docs),
        "retrieved": sorted(retrieved),
        "leakage_vendors": sorted({v for v in leakage if v}),
        "source_count": len({d.metadata.get("source", "") for d in docs}),
    }


async def evaluate_correctness(retriever, extract, golden: list[dict], k: int) -> list[dict]:
    """Correctness end-to-end: bandingkan aturan hasil ekstraksi dengan expected_vendor_rules."""
    out: list[dict] = []
    for example in golden:
        inp = example["inputs"]
        ref = example["reference_outputs"].get("expected_vendor_rules") or {}
        docs = retriever.retrieve(inp["vendor_id"], inp["sku"], k=k)
        rules = await extract(inp["vendor_id"], inp["sku"], docs)
        got_tiers = [(t.min_qty, t.discount_pct) for t in rules.discount_tiers]
        ref_tiers = [(t["min_qty"], t["discount_pct"]) for t in ref.get("discount_tiers", [])]
        out.append(
            {
                "query": inp["query"],
                "vendor_id": inp["vendor_id"],
                "sku": inp["sku"],
                "moq_correct": rules.moq == ref.get("moq", 0),
                "lead_correct": rules.lead_time_days == ref.get("lead_time_days", 7),
                "tiers_correct": got_tiers == ref_tiers,
                "basis": rules.basis,
            }
        )
    return out


def summarize(results: list[dict]) -> dict:
    n = len(results)
    hits = [r["hit"] for r in results]
    recalls = [r["recall"] for r in results]
    leaked = sum(1 for r in results if r["leakage_vendors"])
    facts = [r.get("facts", {}) for r in results]
    return {
        "examples": n,
        "hit_rate_at_k": sum(hits) / n if n else 0.0,
        "recall_at_k": sum(recalls) / n if n else 0.0,
        "leakage_examples": leaked,
        "leakage_rate": leaked / n if n else 0.0,
        "fact_moq": sum(1 for f in facts if f.get("moq")) / n if n else 0.0,
        "fact_lead": sum(1 for f in facts if f.get("lead")) / n if n else 0.0,
        "fact_tiers": sum(f.get("tiers", 0.0) for f in facts) / n if n else 0.0,
    }


def build_retriever(corpus_dir: Path, embeddings=None, store_backend: str = "inmemory"):
    """Bangun retriever dari korpus.

    store_backend:
      - "inmemory" (default): store sementara, aman untuk CI/offline.
      - "pgvector": store produksi (butuh DATABASE_URL postgres + Docker).
        Meniru pola ingest idempoten: delete-by-doc_id lalu add, agar re-run
        evaluasi tidak menduplikasi chunk.
    """
    from app.rag.loader import load_documents

    docs = load_documents(str(corpus_dir))
    if embeddings is None:
        embeddings = DeterministicFakeEmbedding(size=8)
    if store_backend == "pgvector":
        if not settings.database_url.startswith("postgres"):
            sys.exit(
                "store_backend='pgvector' membutuhkan DATABASE_URL postgres. "
                "Jalankan 'docker compose up -d postgres' lalu set DATABASE_URL "
                "di backend/.env (contoh: postgresql+psycopg://procure:procure@localhost:5432/procure)."
            )
        store = build_vector_store(embeddings)
        ids = [doc.id for doc in docs if doc.id]
        try:
            store.delete(ids=ids)
        except Exception:
            pass  # store kosong pada run pertama — delete-by-id tidak masalah
        store.add_documents(docs)
        return VendorRetriever(store)
    store = InMemoryVectorStore(embeddings)
    store.add_documents(docs)
    return VendorRetriever(store)


def run_evaluation(
    corpus_dir: Path = DEFAULT_CORPUS,
    golden_path: Path = DEFAULT_GOLDEN,
    k: int = 8,
    embeddings=None,
    retriever=None,
) -> dict:
    golden = load_golden_set(golden_path)
    if retriever is None:
        retriever = build_retriever(corpus_dir, embeddings=embeddings)
    results = [evaluate_example(retriever, ex, k=k) for ex in golden]
    return {"summary": summarize(results), "results": results}


def _print_report(report: dict) -> None:
    s = report["summary"]
    print("=== Ringkasan Evaluasi Retrieval RAG ===")
    print(f"Contoh: {s['examples']}")
    print(f"hit-rate@k: {s['hit_rate_at_k']:.2f}")
    print(f"recall@k: {s['recall_at_k']:.2f}")
    print(f"contoh bocor lintas vendor: {s['leakage_examples']} ({s['leakage_rate']:.2f})")
    print(f"fakta MOQ ter-retrieve: {s['fact_moq']:.2f}")
    print(f"fakta lead time ter-retrieve: {s['fact_lead']:.2f}")
    print(f"fakta tier diskon ter-retrieve: {s['fact_tiers']:.2f}")
    if report.get("correctness"):
        correctness = report["correctness"]
        n = len(correctness)
        moq = sum(1 for c in correctness if c["moq_correct"])
        lead = sum(1 for c in correctness if c["lead_correct"])
        tiers = sum(1 for c in correctness if c["tiers_correct"])
        print("=== Correctness End-to-End (ekstraksi vs golden) ===")
        print(f"MOQ benar: {moq}/{n}")
        print(f"lead time benar: {lead}/{n}")
        print(f"tier diskon benar: {tiers}/{n}")
        for c in correctness:
            flag = "OK " if c["moq_correct"] and c["lead_correct"] and c["tiers_correct"] else "FAIL"
            print(
                f"[{flag}] {c['vendor_id']}/{c['sku']} moq={c['moq_correct']} "
                f"lead={c['lead_correct']} tiers={c['tiers_correct']} basis={c['basis']}"
            )
    for r in report["results"]:
        flag = "OK " if r["hit"] and not r["leakage_vendors"] else "FAIL"
        print(
            f"[{flag}] {r['vendor_id']} {r['query'][:60]!r} "
            f"recall={r['recall']:.2f} leak={r['leakage_vendors']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluasi kualitas retrieval RAG")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--mode", choices=["deterministic", "llm"], default="deterministic")
    parser.add_argument(
        "--store",
        choices=["inmemory", "pgvector"],
        default="inmemory",
        help="Backend vector store untuk evaluasi (pgvector butuh Docker + DATABASE_URL postgres)",
    )
    args = parser.parse_args()

    embeddings = None
    if args.mode == "llm":
        from app.core.llm import get_embeddings

        embeddings = get_embeddings()

    retriever = build_retriever(args.corpus, embeddings=embeddings, store_backend=args.store)
    report = run_evaluation(args.corpus, args.golden, k=args.k, retriever=retriever)
    if args.mode == "llm":
        import asyncio

        from app.rag.extractor import build_rule_extractor

        golden = load_golden_set(args.golden)
        correctness = asyncio.run(evaluate_correctness(retriever, build_rule_extractor(), golden, k=args.k))
        report["correctness"] = correctness
    _print_report(report)


if __name__ == "__main__":
    main()