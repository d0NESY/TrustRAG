import argparse
from dataclasses import replace
import json
from pathlib import Path
import time

from ragbase.config import load_config
from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl, write_jsonl, sha256_file
from ragbase.evaluation.generation_metrics import generation_metrics
from ragbase.evaluation.judge import GenerationJudge
from ragbase.generation.generator import AnswerGenerator
from ragbase.schema import RetrievalResult


def evaluate(config, retrieval_directory, output_directory=None, no_gate=False):
    retrieval_directory = Path(retrieval_directory)
    directory = Path(output_directory or retrieval_directory)
    directory.mkdir(parents=True, exist_ok=True)
    resolved = json.loads((retrieval_directory / "resolved_config.json").read_text(encoding="utf-8"))
    if resolved["retrieval"] != config.to_dict()["retrieval"] or resolved["chunking"] != config.to_dict()["chunking"]:
        raise ValueError("Generation config differs from saved retrieval experiment")
    if no_gate:
        config = replace(config, name="hybrid_reranker_no_gate", answerability=replace(config.answerability, enabled=False))
    prediction_path = retrieval_directory / "retrieval_predictions.jsonl"
    fingerprint = {"retrieval_predictions_sha256": sha256_file(prediction_path), "config": config.to_dict()}
    lock_path = directory / "generation_run.json"
    if lock_path.exists():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        if lock["fingerprint"] != fingerprint:
            raise ValueError("Cannot change parameters while resuming a generation experiment")
        if lock["state"] == "complete":
            raise RuntimeError("Generation experiment is complete; recompute metrics from predictions instead")
    else:
        write_json(lock_path, {"state": "started", "fingerprint": fingerprint})
    chunks = {chunk["chunk_id"]: chunk for chunk in read_jsonl(retrieval_directory / "chunks.jsonl")}
    rows = {row["id"]: row for row in read_jsonl(retrieval_directory / "benchmark_aligned.jsonl")}
    retrieval_predictions = read_jsonl(prediction_path)
    output_path = directory / "generation_predictions.jsonl"
    outputs = read_jsonl(output_path) if output_path.exists() else []
    completed = {row["id"] for row in outputs}
    generator, judge = AnswerGenerator(config), GenerationJudge(config)
    for position, retrieval in enumerate(retrieval_predictions, 1):
        if retrieval["id"] in completed:
            continue
        row = rows[retrieval["id"]]
        results = [RetrievalResult(**result, text=chunks[result["chunk_id"]]["text"]) for result in retrieval["results"]]
        started = time.perf_counter()
        answer = generator.generate(row["question"], results)
        online_generation_ms = (time.perf_counter() - started) * 1000
        judgment = judge.evaluate(row, answer)
        outputs.append({"id": row["id"], "question": row["question"], "answerable": row["answerable"], "gold_answer": row["answer"],
                        "gold_chunk_ids": row["relevant_chunk_ids"], "ranked_chunk_ids": retrieval["ranked_chunk_ids"],
                        "candidate_chunk_ids": retrieval["candidate_chunk_ids"], "evidence_text": row.get("evidence_text"),
                        **answer.to_dict(), "judge": judgment, "judge_latency_ms": judgment.get("latency_ms", 0.0),
                        "retrieval_latency_ms": retrieval["retrieval_latency_ms"], "reranking_latency_ms": retrieval["reranking_latency_ms"],
                        "total_latency_ms": retrieval["total_latency_ms"] + online_generation_ms})
        # Checkpoint actual model/judge outputs after every sample. Interrupted runs
        # can resume this same frozen experiment without editing predictions.
        write_jsonl(output_path, outputs)
        if position % 5 == 0 or position == len(retrieval_predictions):
            print(f"{config.name} generation: {position}/{len(retrieval_predictions)}", flush=True)
    write_json(directory / "generation_metrics.json", generation_metrics(outputs))
    write_jsonl(directory / "judge_results.jsonl", [{"id": row["id"], **row["judge"]} for row in outputs])
    write_json(directory / "generation_run.json", {"state": "complete", "fingerprint": fingerprint, "count": len(outputs)})
    generation_resolved = {**resolved, **config.to_dict(), "generation_evaluation": "Real model calls; fixed local LLM judge; checkpointed. See saved per-sample judge labels."}
    write_json(directory / "generation_resolved_config.json", generation_resolved)
    with (directory / "run.log").open("a", encoding="utf-8", newline="\n") as log:
        log.write(f"Generation complete: {len(outputs)} real query outcomes, generator={config.llm_model}, judge={config.generation.judge_model}.\n")
    return generation_metrics(outputs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/hybrid_reranker.yaml")
    parser.add_argument("--retrieval", required=True)
    parser.add_argument("--output")
    parser.add_argument("--no-gate", action="store_true")
    args = parser.parse_args()
    evaluate(load_config(args.config), args.retrieval, args.output, args.no_gate)


if __name__ == "__main__":
    main()
