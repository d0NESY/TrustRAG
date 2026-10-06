"""Zero-retuning external run: original Dense+CE, gate off, citations on."""

import json
import os
import time
import argparse

os.environ.setdefault("HF_HUB_OFFLINE", "1")

from ragbase.config import load_config  # noqa: E402
from ragbase.evaluation.artifacts import write_json  # noqa: E402
from ragbase.evaluation.benchmark import align_benchmark, read_jsonl, write_jsonl, sha256_file  # noqa: E402
from ragbase.evaluation.retrieval_metrics import retrieval_metrics  # noqa: E402
from ragbase.evaluation.generation_metrics import generation_metrics  # noqa: E402
from ragbase.evaluation.judge import GenerationJudge  # noqa: E402
from ragbase.generation.generator import AnswerGenerator  # noqa: E402
from ragbase.generation.answerability import evidence_features  # noqa: E402
from ragbase.ingestion.indexer import build_index  # noqa: E402
from ragbase.retrieval.hybrid import RetrievalPipeline  # noqa: E402
from scripts.final_validation.common import ROOT, OUT, REPORTS, prepare, verify_frozen, table  # noqa: E402


def verify_external():
    directory = OUT / "external"
    manifest = json.loads((directory / "dataset_manifest.json").read_text(encoding="utf-8"))
    files = {**manifest["files"], "squad_v2_dev.json": manifest["source_sha256"], "questions.jsonl": manifest["questions_sha256"], "source_contexts.json": manifest["contexts_sha256"]}
    for name, digest in files.items():
        if sha256_file(directory / name) != digest:
            raise ValueError(f"Frozen external input changed: {name}")
    if sha256_file(ROOT / "configs/v2/dense_reranker.yaml") != manifest["config_sha256"]:
        raise ValueError("External final architecture config changed")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-only", action="store_true")
    args = parser.parse_args()
    prepare()
    manifest = verify_external()
    if args.retrieval_only:
        retrieval_only(manifest)
        return
    directory = OUT / "external/run"
    directory.mkdir(exist_ok=True)
    config = load_config(ROOT / "configs/v2/dense_reranker.yaml")
    assert not config.answerability.enabled and config.retrieval.mode == "dense" and config.retrieval.rerank
    from ragbase.evaluation.runtime import verify_runtime
    runtime = verify_runtime(config.generation.base_url)
    key = {"config": config.to_dict(), "dataset_manifest_sha256": sha256_file(OUT / "external/dataset_manifest.json"),
           "core_sha256": json.loads((ROOT / "experiments/v2/formal_v2_freeze.json").read_text())["core_algorithm_sha256"]}
    lock = directory / "run_state.json"
    if lock.exists():
        state = json.loads(lock.read_text())
        if state["fingerprint"] != key:
            raise ValueError("External checkpoint inputs changed")
        if state["state"] == "complete":
            print("External run already complete; no model calls repeated.")
            return
    else:
        write_json(lock, {"state": "started", "fingerprint": key})
    index = build_index((OUT / "external/documents").glob("*.pdf"), config, OUT / "external/indexes")
    try:
        aligned = align_benchmark(read_jsonl(OUT / "external/questions.jsonl"), index.chunks)
        write_jsonl(directory / "benchmark_aligned.jsonl", aligned)
        write_jsonl(directory / "chunks.jsonl", index.chunks)
        write_json(directory / "resolved_config.json", {"config": config.to_dict(), "runtime": runtime, "index": index.manifest, **key,
                   "natural_document_source": manifest["source_url"], "no_retuning": True, "gold_source": manifest["human_gold_source"],
                   "natural_qa_scope_caveat": manifest["scope_caveat"]})
        pipeline, generator, judge = RetrievalPipeline(config, index), AnswerGenerator(config), GenerationJudge(config)
        pipeline.retrieve("What information does this excerpt provide?")
        path = directory / "generation_predictions.jsonl"
        predictions = read_jsonl(path) if path.exists() else []
        done = {row["id"] for row in predictions}
        for position, row in enumerate(aligned, 1):
            if row["id"] in done:
                continue
            batch = pipeline.retrieve(row["question"])
            started = time.perf_counter()
            try:
                output = generator.generate(row["question"], batch.results)
                generation_wall = (time.perf_counter() - started) * 1000
                judgment = judge.evaluate(row, output)
            except Exception as error:
                error_path = directory / "execution_errors.jsonl"
                errors = read_jsonl(error_path) if error_path.exists() else []
                errors.append({"id": row["id"], "position": position, "error": repr(error), "resume_policy": "Retain error journal; identical fingerprint retry only, never drop question."})
                write_jsonl(error_path, errors)
                raise
            predictions.append({"id": row["id"], "question": row["question"], "family_id": row["family_id"], "category": row["category"],
                                "answerable": row["answerable"], "gold_answer": row["answer"], "gold_chunk_ids": row["relevant_chunk_ids"],
                                "evidence_text": row.get("evidence_text"), "native_answers": row["native_answers"],
                                "ranked_chunk_ids": [r.chunk_id for r in batch.results], "candidate_chunk_ids": [r.chunk_id for r in batch.candidates],
                                "results": [r.to_dict(include_text=False) for r in batch.results],
                                "evidence_features": evidence_features([r.score for r in batch.results]), **output.to_dict(), "judge": judgment,
                                "retrieval_latency_ms": batch.retrieval_latency_ms, "reranking_latency_ms": batch.reranking_latency_ms,
                                "retrieval_total_latency_ms": batch.total_latency_ms,
                                "total_latency_ms": batch.total_latency_ms + generation_wall, "judge_latency_ms": judgment.get("latency_ms", 0.0)})
            write_jsonl(path, predictions)
            if position % 5 == 0:
                print(f"External zero-retuning Dense+CE: {position}/75", flush=True)
        if len(predictions) != 75 or {r["id"] for r in predictions} != {r["id"] for r in aligned}:
            raise ValueError("External prediction count/ID mismatch")
        retrieval_rows = [{key: row[key] for key in ["id", "question", "answerable", "gold_chunk_ids", "ranked_chunk_ids", "candidate_chunk_ids", "results", "retrieval_latency_ms", "reranking_latency_ms"]}
                          | {"total_latency_ms": row["retrieval_total_latency_ms"]} for row in predictions]
        write_jsonl(directory / "retrieval_predictions.jsonl", retrieval_rows)
        rmetric = retrieval_metrics(retrieval_rows)
        gmetric = generation_metrics(predictions)
        gmetric["coverage"] = sum(not r["abstained"] for r in predictions) / len(predictions)
        write_json(directory / "retrieval_metrics.json", rmetric)
        write_json(directory / "generation_metrics.json", gmetric)
        write_jsonl(directory / "judge_results.jsonl", [{"id": r["id"], **r["judge"]} for r in predictions])
        write_json(lock, {"state": "complete", "fingerprint": key, "count": len(predictions)})
        synthetic_r = json.loads((ROOT / "experiments/v2/test/dense_reranker/retrieval_metrics.json").read_text())
        synthetic_g = json.loads((ROOT / "experiments/v2/test/G0_prompt_only/generation_metrics.json").read_text())
        text = "# Zero-retuning External Natural Document Test\n\n使用公开 SQuAD2 的 15 个自然 Wikipedia 摘录、75 道原生人工 QA（45 answerable / 30 impossible），与 V1/V2 虚构文档独立。PDF 仅为原文格式转换，全段原文与 gold 原生 offset 已校验；没有 Codex 生成的新事实或新 QA。文档/问题按原数据顺序和预声明计数规则选取，未按结果筛选。\n\n保持 V2 最终 Dense + 原 Cross-Encoder、gate OFF、原 Citation Logic、chunk2048/128、candidate/final K=10、context top5、embedding/reranker/generation/seed 全部不变。所有 75 题含错误都保留。\n\n"
        text += table(["dataset / architecture", "R@1", "R@5", "MRR", "nDCG@5"],
                      [["Synthetic V2 / Dense+CE", *[synthetic_r[k] for k in ["recall@1", "recall@5", "mrr", "ndcg@5"]]],
                       ["External / Dense+CE", *[rmetric[k] for k in ["recall@1", "recall@5", "mrr", "ndcg@5"]]]])
        text += "\n\n生成指标及原 V2 背景参考：\n\n"
        text += table(["dataset / architecture", "Correctness (judge)", "Groundedness (judge)", "Gold-source citation precision", "F1", "FAR", "FRR", "Coverage"],
                      [[name, metric["answer_correctness"], metric["groundedness"], metric["citation_accuracy"], *[metric["answerability"][k] for k in ["f1", "false_answer_rate", "false_refusal_rate"]], coverage]
                       for name, metric, coverage in [("Synthetic V2 G0 / Hybrid+CE", synthetic_g, synthetic_g["coverage"]), ("External / Dense+CE", gmetric, gmetric["coverage"])]])
        text += "\n\n检索部分是同架构跨数据集对照，只描述 cross-dataset generalization gap，不能单独归因为模型退化。V2 没有 Dense+CE 的正式生成数据，所以生成表中的 V2 G0 仅为 Hybrid+CE 背景参考，既变了数据又变了候选来源，不是纯领域效应的受控生成差值；本轮没有补写/重跑 V2 正式生成。\n\n原生 impossible 标签最初针对单段 context，放入多文档 corpus 后的全局有效性尚未独立人工审核。摘录不等于完整真实政策文档，公开 SQuAD 可能进入 Gemma 预训练；不能称为 unseen 自然企业 QA 泛化证明。第一条 native accepted answer 作为原指标参考，其他 native aliases 完整保存；judge 是同一模型族、可出错，引用准确率仍为 gold-source 代理。\n\n"
        text += f"LLM judge failure count={gmetric['judge_failure_count']}；独立项目人工审阅仍为 PENDING_HUMAN_REVIEW。数据源、配置、模型校验和、原输出与完整 gold 保存于 experiments/final_validation/external。\n"
        (REPORTS / "external_test_report.md").write_text(text, encoding="utf-8")
    finally:
        index.close()
    verify_external()
    verify_frozen()
    print("External natural-doc/native-QA run complete; no original V1/V2 output changed.")


def retrieval_only(manifest):
    directory = OUT / "external/retrieval_only"
    directory.mkdir(exist_ok=True)
    config = load_config(ROOT / "configs/v2/dense_reranker.yaml")
    index = build_index((OUT / "external/documents").glob("*.pdf"), config, OUT / "external/indexes")
    try:
        gold = align_benchmark(read_jsonl(OUT / "external/questions.jsonl"), index.chunks)
        pipeline = RetrievalPipeline(config, index)
        pipeline.retrieve("What information does this excerpt provide?")
        path = directory / "retrieval_predictions.jsonl"
        predictions = read_jsonl(path) if path.exists() else []
        finished = {row["id"] for row in predictions}
        for position, row in enumerate(gold, 1):
            if row["id"] in finished:
                continue
            batch = pipeline.retrieve(row["question"])
            predictions.append({"id": row["id"], "question": row["question"], "answerable": row["answerable"],
                                "gold_chunk_ids": row["relevant_chunk_ids"], "ranked_chunk_ids": [r.chunk_id for r in batch.results],
                                "candidate_chunk_ids": [r.chunk_id for r in batch.candidates], "results": [r.to_dict(include_text=False) for r in batch.results],
                                "retrieval_latency_ms": batch.retrieval_latency_ms, "reranking_latency_ms": batch.reranking_latency_ms,
                                "total_latency_ms": batch.total_latency_ms})
            write_jsonl(path, predictions)
            if position % 15 == 0:
                print(f"External retrieval-only: {position}/75", flush=True)
        if len(predictions) != 75 or {r["id"] for r in predictions} != {r["id"] for r in gold}:
            raise ValueError("Incomplete external retrieval IDs")
        metric = retrieval_metrics(predictions)
        write_json(directory / "retrieval_metrics.json", metric)
        write_json(directory / "resolved_config.json", {"config": config.to_dict(), "index": index.manifest, "manifest": manifest,
                   "status": "retrieval complete; generation blocked by same-version CUDA runtime", "dataset_manifest_sha256": sha256_file(OUT / "external/dataset_manifest.json")})
        write_json(directory / "state.json", {"status": "complete", "count": 75, "answerable": 45})
        write_jsonl(directory / "benchmark_aligned.jsonl", gold)
    finally:
        index.close()
    verify_frozen()
    verify_external()
    print("All 75 external retrieval results saved; generation failure remains explicit.")


if __name__ == "__main__":
    main()
