"""Measure original Dense k=5 and original FlashRank top_n=3 on frozen dev gold.

Imports the git-archive upstream snapshot, not the evolving TrustRAG implementation.
"""

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / ".runtime" / "upstream"
sys.path.insert(0, str(UPSTREAM))
os.environ["FASTEMBED_CACHE_PATH"] = str(ROOT / ".runtime" / "fastembed")

from flashrank import Ranker
defaults = list(Ranker.__init__.__defaults__)
defaults[1] = str(ROOT / ".runtime" / "flashrank")
Ranker.__init__.__defaults__ = tuple(defaults)

from ragbase.config import Config
from ragbase.ingestor import Ingestor
from ragbase.model import create_reranker, create_embeddings
from langchain_qdrant import Qdrant


def load_support_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "ragbase" / "evaluation" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev"], default="dev")
    parser.add_argument("--reuse-index", action="store_true")
    args = parser.parse_args()
    benchmark = load_support_module("benchmark")
    metrics = load_support_module("retrieval_metrics")
    benchmark.verify_manifest(ROOT)
    index_path = ROOT / ".runtime" / "upstream-benchmark" / "qdrant"
    Config.Path.DATABASE_DIR = index_path
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.exists() and not args.reuse_index:
        raise RuntimeError("Upstream baseline already has an index; explicitly use --reuse-index to evaluate it")
    if args.reuse_index:
        store = Qdrant.from_existing_collection(embedding=create_embeddings(), collection_name=Config.Database.DOCUMENTS_COLLECTION, path=index_path)
        ingestion_ms = None
    else:
        started = time.perf_counter()
        store = Ingestor().ingest(sorted((ROOT / "data/documents").glob("*.pdf")))
        ingestion_ms = (time.perf_counter() - started) * 1000
    points, _ = store.client.scroll(collection_name=Config.Database.DOCUMENTS_COLLECTION, limit=10000, with_payload=True)
    chunks = [{"chunk_id": hashlib.sha256(point.payload["page_content"].encode()).hexdigest(), "text": point.payload["page_content"], "metadata": point.payload.get("metadata", {})} for point in points]
    rows = benchmark.align_benchmark(benchmark.read_jsonl(ROOT / f"data/benchmark/{args.split}.jsonl"), chunks)
    retriever = store.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    reranker = create_reranker()
    outputs = {"dense": [], "dense_reranker": []}
    # Exclude model initialization and warm-up from per-query retrieval timing.
    retriever.invoke("What is the employee handbook?")
    reranker.compress_documents(retriever.invoke("What is the expense policy?"), "What is the expense policy?")
    for i, row in enumerate(rows):
        start = time.perf_counter()
        dense = retriever.invoke(row["question"])
        dense_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        reranked = reranker.compress_documents(dense, row["question"])
        rerank_ms = (time.perf_counter() - start) * 1000
        for method, docs, ranking_ms in [("dense", dense, 0.0), ("dense_reranker", reranked, rerank_ms)]:
            outputs[method].append({"id": row["id"], "question": row["question"], "answerable": row["answerable"], "gold_chunk_ids": row["relevant_chunk_ids"], "ranked_chunk_ids": [hashlib.sha256(doc.page_content.encode()).hexdigest() for doc in docs], "retrieved": [{"text": doc.page_content, "metadata": doc.metadata} for doc in docs], "retrieval_latency_ms": dense_ms, "reranking_latency_ms": ranking_ms, "total_latency_ms": dense_ms + ranking_ms})
        print(f"Original baseline {i + 1}/{len(rows)}", flush=True)
    summaries = {}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for method, predictions in outputs.items():
        directory = ROOT / "experiments" / method / "upstream_dev_baseline"
        directory.mkdir(parents=True, exist_ok=True)
        config = {"name": method, "source_commit": "5af7b79162329fa0b725b39d1aeeea7eb1e4428b", "git_commit": commit, "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(), "split": "dev", "embedding_model": Config.Model.EMBEDDINGS, "reranker_model": Config.Model.RERANKER if method == "dense_reranker" else None, "chunking": "original whole-document semantic + recursive; 2048/128", "dense_top_k": 5, "final_top_k": 3 if method == "dense_reranker" else 5, "ingestion_ms": ingestion_ms, "chunk_count": len(chunks), "corpus_version": "northstar-v1", "benchmark_sha256": benchmark.sha256_file(ROOT / "data/benchmark/dev.jsonl"), "llm": None, "generation": "not run in this retrieval-only original baseline"}
        for name in ["config.json", "resolved_config.json"]:
            (directory / name).write_text(json.dumps(config, indent=2), encoding="utf-8")
        benchmark.write_jsonl(directory / "retrieval_predictions.jsonl", predictions)
        summary = metrics.retrieval_metrics(predictions)
        summaries[method] = summary
        (directory / "retrieval_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (directory / "run.log").write_text(f"Actual upstream retrieval evaluation; {len(predictions)} dev questions; ingestion_ms={ingestion_ms}; index_reused={args.reuse_index}.\n", encoding="utf-8")
    report = ["# Original RagBase retrieval baseline (dev only)", "", "Actual measurements using the frozen upstream source and whole-document chunking. The original dense depth is 5 and FlashRank returns at most 3; Recall@10 is therefore capped by the saved ranking depth. These results precede retrieval algorithm changes and are separate from the later controlled five-method comparison.", "", "| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@5 | Mean ms | P50 ms | P95 ms |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for method, summary in summaries.items():
        values = [summary[key] for key in ["recall@1", "recall@3", "recall@5", "recall@10", "mrr", "ndcg@5"]] + [summary["total_latency_ms"][key] for key in ["mean_ms", "p50_ms", "p95_ms"]]
        report.append("| " + method + " | " + " | ".join(f"{value:.4f}" for value in values) + " |")
    (ROOT / "docs/original_baseline_results.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(summaries, indent=2), flush=True)
    store.client.close()


if __name__ == "__main__":
    main()
