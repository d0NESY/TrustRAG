import argparse
from pathlib import Path

from ragbase.config import load_config
from ragbase.evaluation.artifacts import ROOT, provenance, save_retrieval_run, write_json
from ragbase.evaluation.benchmark import align_benchmark, read_jsonl, verify_manifest, write_jsonl, sha256_file
from ragbase.evaluation.retrieval_metrics import retrieval_metrics
from ragbase.ingestion.indexer import build_index
from ragbase.retrieval.hybrid import RetrievalPipeline


def evaluate(config, index, split="dev", directory=None):
    benchmark_path = ROOT / f"data/benchmark/{split}.jsonl"
    aligned = align_benchmark(read_jsonl(benchmark_path), index.chunks)
    directory = Path(directory or ROOT / "experiments" / config.name / split)
    directory.mkdir(parents=True, exist_ok=True)
    checkpoint = directory / "retrieval_predictions.jsonl"
    fingerprint = {"config": config.to_dict(), "index_id": index.manifest["index_id"], "benchmark_sha256": sha256_file(benchmark_path)}
    if split == "test":
        lock = directory / "retrieval_test_run.json"
        if lock.exists():
            import json
            previous = json.loads(lock.read_text(encoding="utf-8"))
            if previous["fingerprint"] != fingerprint:
                raise RuntimeError("Cannot alter a started formal test experiment")
            if previous["state"] == "complete":
                raise RuntimeError("Formal test retrieval complete; recompute saved predictions instead")
        else:
            write_json(lock, {"state": "started", "fingerprint": fingerprint})
    resolved = provenance(config, split, index, benchmark_path)
    pipeline = RetrievalPipeline(config, index)
    pipeline.retrieve("What is the expense policy?")
    predictions = read_jsonl(checkpoint) if split == "test" and checkpoint.exists() else []
    completed = {row["id"] for row in predictions}
    for position, row in enumerate(aligned, 1):
        if row["id"] in completed:
            continue
        batch = pipeline.retrieve(row["question"])
        predictions.append({"id": row["id"], "question": row["question"], "answerable": row["answerable"], "gold_chunk_ids": row["relevant_chunk_ids"],
                            "ranked_chunk_ids": [result.chunk_id for result in batch.results], "candidate_chunk_ids": [result.chunk_id for result in batch.candidates],
                            "results": [result.to_dict(include_text=False) for result in batch.results],
                            "retrieval_latency_ms": batch.retrieval_latency_ms, "reranking_latency_ms": batch.reranking_latency_ms, "total_latency_ms": batch.total_latency_ms})
        if split == "test":
            write_jsonl(checkpoint, predictions)
        if position % 10 == 0 or position == len(aligned):
            print(f"{config.name} {split}: {position}/{len(aligned)}", flush=True)
    summary = retrieval_metrics(predictions)
    save_retrieval_run(directory, resolved, aligned, predictions, summary, index.chunks)
    if split == "test":
        write_json(directory / "retrieval_test_run.json", {"state": "complete", "fingerprint": fingerprint, "count": len(predictions)})
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/baseline.yaml")
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--output")
    args = parser.parse_args()
    verify_manifest(ROOT)
    config = load_config(args.config)
    index = build_index((ROOT / "data/documents").glob("*.pdf"), config)
    try:
        summary = evaluate(config, index, args.split, args.output)
        print(f"Recall@5={summary['recall@5']:.4f}, MRR={summary['mrr']:.4f}, nDCG@5={summary['ndcg@5']:.4f}")
    finally:
        index.close()


if __name__ == "__main__":
    main()
