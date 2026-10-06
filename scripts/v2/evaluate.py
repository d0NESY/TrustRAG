"""V2 controlled runs using unchanged V1 classes, with separate checkpoints."""

from dataclasses import replace
from datetime import datetime
import json
import os
import time
from zoneinfo import ZoneInfo

os.environ.setdefault("HF_HUB_OFFLINE", "1")

from ragbase.config import load_config  # noqa: E402
from ragbase.evaluation.artifacts import write_json  # noqa: E402
from ragbase.evaluation.benchmark import align_benchmark, read_jsonl, sha256_file, write_jsonl  # noqa: E402
from ragbase.evaluation.generation_metrics import generation_metrics  # noqa: E402
from ragbase.evaluation.judge import GenerationJudge  # noqa: E402
from ragbase.evaluation.retrieval_metrics import retrieval_metrics  # noqa: E402
from ragbase.generation.answerability import evidence_features  # noqa: E402
from ragbase.generation.generator import AnswerGenerator  # noqa: E402
from ragbase.ingestion.indexer import build_index  # noqa: E402
from ragbase.retrieval.hybrid import RetrievalPipeline  # noqa: E402
from ragbase.schema import RetrievalResult  # noqa: E402
from scripts.v2.common import ROOT, DATA, EXPERIMENTS, git_commit, verify_v1  # noqa: E402

METHODS = ["dense", "bm25", "dense_reranker", "hybrid", "hybrid_reranker"]


def verify_dataset():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["files"].items():
        if sha256_file(DATA / name) != digest:
            raise ValueError(f"V2 benchmark changed: {name}")
    return manifest


def freeze_run(configs):
    v1 = verify_v1()
    verify_dataset()
    conditions = {"configs": [config.to_dict() for config in configs], "core_algorithm_sha256": v1["core_algorithm_sha256"],
                  "benchmark_manifest_sha256": sha256_file(DATA / "manifest.json"),
                  "model_artifacts_sha256": sha256_file(ROOT / "docs/model_artifacts.json"),
                  "splits": ["dev", "test"], "gate_conditions": ["G0_prompt_only", "G1_current_v1_gate"],
                  "gate_threshold": load_config(ROOT / "configs/v2/current_gate.yaml").to_dict()["answerability"],
                  "candidate_depth": 10, "final_depth": 10, "tuning": "none; frozen V1 algorithm round"}
    path = EXPERIMENTS / "formal_v2_freeze.json"
    if path.exists():
        if json.loads(path.read_text()) != conditions:
            raise ValueError("Frozen V2 run inputs changed; do not overwrite its results")
    else:
        write_json(path, conditions)
    return conditions


def evaluate_retrieval(config, index, split):
    directory = EXPERIMENTS / split / config.name
    directory.mkdir(parents=True, exist_ok=True)
    aligned = align_benchmark(read_jsonl(DATA / (split + ".jsonl")), index.chunks)
    key = {"config": config.to_dict(), "index_id": index.manifest["index_id"], "questions_sha256": sha256_file(DATA / (split + ".jsonl"))}
    lock = directory / "run_state.json"
    if lock.exists():
        state = json.loads(lock.read_text())
        if state["fingerprint"] != key:
            raise ValueError("Retrieval checkpoint parameters changed")
        if state["state"] == "complete":
            return
    else:
        write_json(lock, {"state": "started", "fingerprint": key})
    write_json(directory / "resolved_config.json", {**config.to_dict(), "git_commit": git_commit(),
               "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(), "benchmark_version": "meridian-hard-v2.0", "split": split,
               "core_algorithm_sha256": verify_v1()["core_algorithm_sha256"], "index": index.manifest, "question_sha256": key["questions_sha256"],
               "latency_definition": "Warm models; real query embedding/search/fusion; reranking separate; no cached query embeddings."})
    write_json(directory / "config.json", config.to_dict())
    write_jsonl(directory / "benchmark_aligned.jsonl", aligned)
    write_jsonl(directory / "chunks.jsonl", index.chunks)
    path = directory / "retrieval_predictions.jsonl"
    predictions = read_jsonl(path) if path.exists() else []
    finished = {row["id"] for row in predictions}
    pipeline = RetrievalPipeline(config, index)
    pipeline.retrieve("Which record owns the request?")
    for position, row in enumerate(aligned, 1):
        if row["id"] in finished:
            continue
        batch = pipeline.retrieve(row["question"])
        predictions.append({"id": row["id"], "family_id": row["family_id"], "category": row["category"], "split": split,
                            "question": row["question"], "answerable": row["answerable"], "gold_chunk_ids": row["relevant_chunk_ids"],
                            "ranked_chunk_ids": [result.chunk_id for result in batch.results],
                            "candidate_chunk_ids": [result.chunk_id for result in batch.candidates],
                            "candidate_scores": [result.score for result in batch.candidates],
                            "results": [result.to_dict(include_text=False) for result in batch.results],
                            "retrieval_latency_ms": batch.retrieval_latency_ms, "reranking_latency_ms": batch.reranking_latency_ms,
                            "total_latency_ms": batch.total_latency_ms})
        write_jsonl(path, predictions)
        if position % 20 == 0 or position == len(aligned):
            print(f"V2 {config.name} {split}: {position}/{len(aligned)}", flush=True)
    metric = retrieval_metrics(predictions)
    positive = [row for row in predictions if row["answerable"]]
    metric["candidate_depth"] = config.retrieval.fusion_top_k if config.retrieval.mode == "hybrid" else (config.retrieval.sparse_top_k if config.retrieval.mode == "bm25" else config.retrieval.dense_top_k)
    metric["candidate_recall"] = sum(len(set(row["candidate_chunk_ids"]) & set(row["gold_chunk_ids"])) / len(set(row["gold_chunk_ids"])) for row in positive) / len(positive)
    metric["candidate_hit_rate"] = sum(bool(set(row["candidate_chunk_ids"]) & set(row["gold_chunk_ids"])) for row in positive) / len(positive)
    write_json(directory / "retrieval_metrics.json", metric)
    write_json(lock, {"state": "complete", "fingerprint": key, "count": len(predictions)})
    (directory / "run.log").write_text(f"Actual V2 {split}; {len(predictions)} questions; frozen V1 algorithm; candidate depth {metric['candidate_depth']}.\n", encoding="utf-8", newline="\n")
    verify_v1()


def evaluate_gate(split, enabled):
    source = EXPERIMENTS / split / "hybrid_reranker"
    label = "G1_current_v1_gate" if enabled else "G0_prompt_only"
    directory = EXPERIMENTS / split / label
    directory.mkdir(parents=True, exist_ok=True)
    base = load_config(ROOT / "configs/v2/current_gate.yaml")
    config = replace(base, name=label, answerability=replace(base.answerability, enabled=enabled))
    key = {"config": config.to_dict(), "retrieval_sha256": sha256_file(source / "retrieval_predictions.jsonl")}
    lock = directory / "run_state.json"
    if lock.exists():
        state = json.loads(lock.read_text())
        if state["fingerprint"] != key:
            raise ValueError("Gate checkpoint changed")
        if state["state"] == "complete":
            return
    else:
        write_json(lock, {"state": "started", "fingerprint": key})
    write_json(directory / "config.json", config.to_dict())
    resolved = json.loads((source / "resolved_config.json").read_text())
    write_json(directory / "resolved_config.json", {**resolved, **config.to_dict(), "gate_condition": label,
               "definition": "G0 retains the frozen grounding prompt and citation-ID check, with evidence-score gate disabled. G1 changes only the V1 gate flag."})
    chunks = {row["chunk_id"]: row for row in read_jsonl(source / "chunks.jsonl")}
    gold = {row["id"]: row for row in read_jsonl(source / "benchmark_aligned.jsonl")}
    retrieval = read_jsonl(source / "retrieval_predictions.jsonl")
    path = directory / "generation_predictions.jsonl"
    predictions = read_jsonl(path) if path.exists() else []
    finished = {row["id"] for row in predictions}
    generator, judge = AnswerGenerator(config), GenerationJudge(config)
    for position, retrieved in enumerate(retrieval, 1):
        if retrieved["id"] in finished:
            continue
        row = gold[retrieved["id"]]
        results = [RetrievalResult(**result, text=chunks[result["chunk_id"]]["text"]) for result in retrieved["results"]]
        features = evidence_features([result.score for result in results])
        started = time.perf_counter()
        output = generator.generate(row["question"], results)
        wall_ms = (time.perf_counter() - started) * 1000
        # Reference answer enters the offline judge only, never the answer generator.
        judgment = judge.evaluate(row, output)
        predictions.append({"id": row["id"], "family_id": row["family_id"], "category": row["category"], "split": split,
                            "question": row["question"], "answerable": row["answerable"], "gold_answer": row["answer"],
                            "gold_chunk_ids": row["relevant_chunk_ids"], "ranked_chunk_ids": retrieved["ranked_chunk_ids"],
                            "candidate_chunk_ids": retrieved["candidate_chunk_ids"], "evidence_text": row.get("evidence_text"),
                            "evidence_features": features, **output.to_dict(), "judge": judgment, "judge_latency_ms": judgment.get("latency_ms", 0.0),
                            "retrieval_latency_ms": retrieved["retrieval_latency_ms"], "reranking_latency_ms": retrieved["reranking_latency_ms"],
                            "total_latency_ms": retrieved["total_latency_ms"] + wall_ms})
        write_jsonl(path, predictions)
        if position % 10 == 0 or position == len(retrieval):
            print(f"V2 {label} {split}: {position}/{len(retrieval)}", flush=True)
    summary = generation_metrics(predictions)
    summary["coverage"] = sum(not row["abstained"] for row in predictions) / len(predictions)
    write_json(directory / "generation_metrics.json", summary)
    write_jsonl(directory / "judge_results.jsonl", [{"id": row["id"], **row["judge"]} for row in predictions])
    write_json(lock, {"state": "complete", "fingerprint": key, "count": len(predictions)})
    (directory / "run.log").write_text(f"Actual V2 {split} generation and fixed LLM judge; condition={label}; {len(predictions)} outcomes.\n", encoding="utf-8", newline="\n")
    verify_v1()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["retrieval", "gate", "all"], default="all")
    parser.add_argument("--split", choices=["dev", "test", "both"], default="both")
    args = parser.parse_args()
    configs = [load_config(ROOT / "configs/v2" / (name + ".yaml")) for name in METHODS]
    freeze_run(configs)
    from ragbase.evaluation.runtime import verify_runtime
    verify_runtime(configs[0].generation.base_url)
    splits = ["dev", "test"] if args.split == "both" else [args.split]
    if args.phase in ["retrieval", "all"]:
        index = build_index((DATA / "documents").glob("*.pdf"), configs[0], ROOT / ".runtime/indexes_v2")
        try:
            for split in splits:
                for config in configs:
                    evaluate_retrieval(config, index, split)
        finally:
            index.close()
    if args.phase in ["gate", "all"]:
        for split in splits:
            for enabled in [False, True]:
                evaluate_gate(split, enabled)
    verify_v1()
    print("V2 requested frozen phase complete; V1 hashes unchanged.", flush=True)


if __name__ == "__main__":
    main()
