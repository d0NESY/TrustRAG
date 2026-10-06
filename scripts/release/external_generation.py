"""Only run after a same-conditions recovery; reuse frozen retrieval inputs."""

import json
import time

from ragbase.config import load_config
from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl, write_jsonl, sha256_file
from ragbase.evaluation.generation_metrics import generation_metrics
from ragbase.evaluation.judge import GenerationJudge
from ragbase.generation.generator import AnswerGenerator
from ragbase.schema import RetrievalResult
from scripts.release.common import ROOT, RELEASE, begin, verify, now, write_md


def main():
    begin()
    recovery = json.loads((RELEASE / "external_generation_status.json").read_text(encoding="utf-8"))
    if recovery["status"] != "RECOVERED":
        raise ValueError("No successful original-runtime recovery; do not substitute a model")
    directory = ROOT / "experiments/final_validation/external_generation"
    directory.mkdir(exist_ok=True)
    config = load_config(ROOT / "configs/v2/dense_reranker.yaml")
    source = ROOT / "experiments/final_validation/external/retrieval_only"
    key = {"config": config.to_dict(), "retrieval_sha256": sha256_file(source / "retrieval_predictions.jsonl"),
           "external_manifest_sha256": sha256_file(ROOT / "experiments/final_validation/external/dataset_manifest.json"), "zero_retuning": True}
    lock = directory / "run_state.json"
    if lock.exists():
        state = json.loads(lock.read_text())
        if state["fingerprint"] != key:
            raise ValueError("External generation conditions changed")
        if state["state"] == "complete":
            return
    else:
        write_json(lock, {"state": "started", "fingerprint": key, "timestamp": now()})
    gold = {row["id"]: row for row in read_jsonl(source / "benchmark_aligned.jsonl")}
    chunks = {row["chunk_id"]: row for row in read_jsonl(ROOT / "experiments/final_validation/external/run/chunks.jsonl")}
    retrieval = read_jsonl(source / "retrieval_predictions.jsonl")
    output_path = directory / "generation_predictions.jsonl"
    rows = read_jsonl(output_path) if output_path.exists() else []
    done = {row["id"] for row in rows}
    generator, judge = AnswerGenerator(config), GenerationJudge(config)
    write_json(directory / "resolved_config.json", {**key, "model_artifacts": json.loads((ROOT / "docs/model_artifacts.json").read_text()), "timestamp": now()})
    for position, retrieved in enumerate(retrieval, 1):
        if retrieved["id"] in done:
            continue
        row = gold[retrieved["id"]]
        results = [RetrievalResult(**result, text=chunks[result["chunk_id"]]["text"]) for result in retrieved["results"]]
        started = time.perf_counter()
        try:
            output = generator.generate(row["question"], results)
            wall_ms = (time.perf_counter() - started) * 1000
            judgment = judge.evaluate(row, output)
        except Exception as error:
            path = directory / "execution_errors.jsonl"
            errors = read_jsonl(path) if path.exists() else []
            errors.append({"id": row["id"], "timestamp": now(), "error": repr(error), "retained": True})
            write_jsonl(path, errors)
            write_json(RELEASE / "external_generation_status.json", {"status": "BLOCKED", "attempts": recovery["attempts"], "maximum_attempts": 3,
                       "partial_predictions": len(rows), "same_frozen_model_and_config": True, "error": repr(error)})
            write_md(RELEASE / "EXTERNAL_GENERATION_BLOCKED.md", "# External Generation：BLOCKED\n\n原条件 probe 恢复后，完整75题运行再次发生已记录错误；保留全部部分预测/错误，不更换模型或新增无限恢复尝试。完整生成指标不发布为最终结果。\n\n" + repr(error))
            raise
        rows.append({"id": row["id"], "question": row["question"], "answerable": row["answerable"], "gold_answer": row["answer"],
                     "gold_chunk_ids": row["relevant_chunk_ids"], "ranked_chunk_ids": retrieved["ranked_chunk_ids"],
                     "candidate_chunk_ids": retrieved["candidate_chunk_ids"], **output.to_dict(), "judge": judgment,
                     "retrieval_latency_ms": retrieved["retrieval_latency_ms"], "reranking_latency_ms": retrieved["reranking_latency_ms"],
                     "judge_latency_ms": judgment.get("latency_ms", 0), "total_latency_ms": retrieved["total_latency_ms"] + wall_ms})
        write_jsonl(output_path, rows)
        if position % 5 == 0:
            print(f"Recovered zero-retuning external generation: {position}/75", flush=True)
    if len(rows) != 75 or {row["id"] for row in rows} != set(gold):
        raise ValueError("Incomplete external generation")
    metrics = generation_metrics(rows)
    metrics["coverage"] = sum(not row["abstained"] for row in rows) / len(rows)
    write_json(directory / "generation_metrics.json", metrics)
    write_jsonl(directory / "judge_results.jsonl", [{"id": row["id"], **row["judge"]} for row in rows])
    write_json(lock, {"state": "complete", "fingerprint": key, "count": len(rows), "timestamp": now()})
    write_json(RELEASE / "external_generation_status.json", {"status": "COMPLETE", "attempts": recovery["attempts"], "maximum_attempts": 3,
               "same_frozen_model_and_config": True, "count": len(rows)})
    write_md(RELEASE / "external_generation_results.md", "# Zero-retuning External Generation\n\n原模型/参数/75题全部保持冻结，无数据过滤，全部预测与judge保存。以下为固定本地同模型族judge指标，非独立人工验证。\n\n```json\n" + json.dumps(metrics, ensure_ascii=False, indent=2) + "\n```\n\n引用precision仍为source-level归属代理；SQuAD摘录规模小、原生impossible仅单段scope、公开数据可能进入预训练，不能宣称自然企业生产准确率。\n")
    verify()


if __name__ == "__main__":
    main()
