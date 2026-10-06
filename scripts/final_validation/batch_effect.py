"""Composition-only probe with fixed query, target, competitor and model."""

import hashlib
import json
import os
from statistics import mean, stdev
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")

from tokenizers import Tokenizer  # noqa: E402
from ragbase.config import load_config  # noqa: E402
from ragbase.evaluation.artifacts import write_json  # noqa: E402
from ragbase.evaluation.benchmark import read_jsonl, write_jsonl  # noqa: E402
from ragbase.retrieval.reranker import CrossEncoderReranker  # noqa: E402
from ragbase.schema import RetrievalResult  # noqa: E402
from scripts.final_validation.common import ROOT, OUT, REPORTS, prepare, verify_frozen, retrieval, csv_write, table  # noqa: E402


def plan():
    prepare()
    directory = OUT / "batch_effect"
    directory.mkdir(exist_ok=True)
    dense, hybrid = retrieval("dense_reranker"), retrieval("hybrid_reranker")
    chunks = {row["chunk_id"]: row for row in read_jsonl(ROOT / "experiments/v2/test/dense_reranker/chunks.jsonl")}
    repeat = json.loads((OUT / "repeatability/protocol.json").read_text())
    mandatory = ["v2_parental_requests_version_conflict", "v2_research_data_version_conflict"]
    maximum = {}
    for identity in repeat["question_ids"]:
        left = {r["chunk_id"]: r["score"] for r in dense[identity]["results"]}
        right = {r["chunk_id"]: r["score"] for r in hybrid[identity]["results"]}
        maximum[identity] = max(abs(left[key] - right[key]) for key in left.keys() & right.keys())
    selected = mandatory + [identity for identity in sorted(maximum, key=lambda identity: (-maximum[identity], identity)) if identity not in mandatory][:4]
    cases = []
    for identity in selected:
        left, right = dense[identity], hybrid[identity]
        target = left["gold_chunk_ids"][0]
        shared = set(left["candidate_chunk_ids"]) & set(right["candidate_chunk_ids"])
        # Hold the nearest shared competing passage fixed at slot 1 too.
        competitor = next(r["chunk_id"] for r in right["results"] if r["chunk_id"] in shared and r["chunk_id"] != target)
        prefix = [target, competitor]
        sets = {"A_dense": prefix + [key for key in left["candidate_chunk_ids"] if key not in prefix],
                "B_hybrid": prefix + [key for key in right["candidate_chunk_ids"] if key not in prefix],
                "C_long_distractors": prefix + sorted([key for key in chunks if key not in prefix], key=lambda key: (-len(chunks[key]["text"]), key))[:8],
                "single_pair": [target]}
        if any(len(value) != (1 if name == "single_pair" else 10) for name, value in sets.items()):
            raise ValueError("Probe candidate budgets differ unexpectedly")
        pair_hash = hashlib.sha256((left["question"] + "\0" + chunks[target]["text"]).encode()).hexdigest()
        cases.append({"id": identity, "question": left["question"], "category": left["category"], "target": target,
                      "fixed_competitor": competitor, "query_target_sha256": pair_hash, "candidate_sets": sets})
    value = {"repeats": 3, "cases": cases, "definition": "A/B/C all 10 candidates. Same query+target at slot0 and same competitor at slot1; only other eight passages vary. Single-pair uses existing API. No inference-code or tokenizer changes."}
    path = directory / "protocol.json"
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError("Batch probe protocol changed")
    else:
        write_json(path, value)
    return value, chunks


def main():
    value, chunks = plan()
    directory = OUT / "batch_effect"
    config = load_config(ROOT / "configs/v2/dense_reranker.yaml")
    from ragbase.evaluation.runtime import verify_runtime
    verify_runtime(config.generation.base_url)
    reranker = CrossEncoderReranker(config)
    client = reranker.client
    unpadded = Tokenizer.from_str(client.tokenizer.to_str())
    unpadded.no_padding()
    unpadded.no_truncation()
    path = directory / "predictions.jsonl"
    rows = read_jsonl(path) if path.exists() else []
    done = {(row["id"], row["condition"], row["repeat"]) for row in rows}
    for case in value["cases"]:
        warm_ids = case["candidate_sets"]["A_dense"]
        def results_for(ids):
            return [RetrievalResult(key, chunks[key]["document_id"], 0.0, position, chunks[key]["text"], chunks[key]["metadata"]) for position, key in enumerate(ids, 1)]
        reranker.rerank(case["question"], results_for(warm_ids), 10)
        for number in range(1, 4):
            for name, identities in case["candidate_sets"].items():
                if (case["id"], name, number) in done:
                    continue
                pairs = [[case["question"], chunks[key]["text"]] for key in identities]
                padded = client.tokenizer.encode_batch(pairs)
                actual_nonpad = [sum(item.attention_mask) for item in padded]
                raw_lengths = [len(item.ids) for item in unpadded.encode_batch(pairs)]
                started = time.perf_counter()
                ranked = reranker.rerank(case["question"], results_for(identities), 10)
                elapsed = (time.perf_counter() - started) * 1000
                target = next(result for result in ranked if result.chunk_id == case["target"])
                competitor = next((result for result in ranked if result.chunk_id == case["fixed_competitor"]), None)
                rows.append({"id": case["id"], "category": case["category"], "condition": name, "repeat": number,
                             "query_target_sha256": case["query_target_sha256"], "candidate_chunk_ids": identities,
                             "candidate_count": len(identities), "target_score": target.score, "target_rank": target.rank,
                             "competitor_score": competitor.score if competitor else None,
                             "target_competitor_margin": target.score - competitor.score if competitor else None,
                             "top1_chunk": ranked[0].chunk_id, "top5_chunks": [r.chunk_id for r in ranked[:5]],
                             "top10_chunks": [r.chunk_id for r in ranked], "padded_token_lengths": [len(item.ids) for item in padded],
                             "nonpad_token_lengths": actual_nonpad, "untruncated_token_lengths": raw_lengths,
                             "target_nonpad_tokens": actual_nonpad[0], "target_padding_tokens": len(padded[0].ids) - actual_nonpad[0],
                             "reranking_latency_ms": elapsed, "results": [r.to_dict(include_text=False) for r in ranked]})
                write_jsonl(path, rows)
        print(f"Batch composition probe complete: {case['id']}", flush=True)
    if len(rows) != 6 * 4 * 3:
        raise ValueError("Incomplete batch composition test")
    csv_rows = [{key: row[key] for key in ["id", "category", "condition", "repeat", "query_target_sha256", "candidate_count", "target_score", "target_rank", "competitor_score", "target_competitor_margin", "top1_chunk", "target_nonpad_tokens", "target_padding_tokens", "reranking_latency_ms"]}
                | {key: json.dumps(row[key]) for key in ["padded_token_lengths", "nonpad_token_lengths", "untruncated_token_lengths"]} for row in rows]
    csv_write(REPORTS / "reranker_batch_scores.csv", csv_rows)
    summary = []
    for case in value["cases"]:
        scores_by_set, margins_by_set = {}, {}
        for name in case["candidate_sets"]:
            part = [row for row in rows if row["id"] == case["id"] and row["condition"] == name]
            scores = [row["target_score"] for row in part]
            scores_by_set[name] = mean(scores)
            margins_by_set[name] = mean(row["target_competitor_margin"] for row in part) if name != "single_pair" else None
            summary.append({"id": case["id"], "condition": name, "mean_target_score": mean(scores), "std_target_score": stdev(scores),
                            "target_score_range": max(scores) - min(scores), "min_rank": min(row["target_rank"] for row in part),
                            "max_rank": max(row["target_rank"] for row in part), "target_top1_rate": mean(float(row["target_rank"] == 1) for row in part),
                            "target_top5_rate": mean(float(row["target_rank"] <= 5) for row in part), "target_competitor_margin": margins_by_set[name]})
        case["score_range_across_conditions"] = max(scores_by_set.values()) - min(scores_by_set.values())
        case["fixed_pair_order_reversed"] = min(margins_by_set[name] for name in ["A_dense", "B_hybrid", "C_long_distractors"]) < 0 < max(margins_by_set[name] for name in ["A_dense", "B_hybrid", "C_long_distractors"])
    csv_write(REPORTS / "reranker_batch_summary.csv", summary)
    write_json(REPORTS / "reranker_batch_effect.json", {"cases": value["cases"], "condition_summary": summary,
               "pair_order_reversal_count": sum(case["fixed_pair_order_reversed"] for case in value["cases"]),
               "mechanism": "Composition effect is directly probed; padding/quantization causal contribution remains a mechanism hypothesis; no ablation changes model/code."})
    report = "# Reranker Candidate Batch Composition Test\n\n六道已观察到 shared-score drift 的诊断题，含两道版本 top1 reversal。固定 query、target 文本、competitor 文本及其 slot0/slot1；A/B/C 仅替换另外八个候选，size=10。另做既有 API 的 single-pair，所有条件各真实执行三次。\n\n"
    report += table(["id", "set", "score mean", "score std", "rank min", "rank max", "top1 rate", "top5 rate", "target-competitor margin"],
                    [[row[key] for key in ["id", "condition", "mean_target_score", "std_target_score", "min_rank", "max_rank", "target_top1_rate", "target_top5_rate", "target_competitor_margin"]] for row in summary])
    report += "\n\n不同集合的 rank 改变也可能来自竞争候选不同，不能全部归给 score 数值漂移。固定 target/competitor 的 margin 变号才直接说明同一对 passage 在其他候选变化时相对顺序改变；single-pair 的 rank=1 是结构性结果。完整 token/padding 长度、top1/top5/top10 与原始分数保存在独立 predictions。\n\n"
    report += f"固定 passage pair 相对次序变号的 case 数：{sum(case['fixed_pair_order_reversed'] for case in value['cases'])}。动态 padding、ONNX 量化均为 mechanism hypothesis；这里没有改换权重/推理代码或做可归因单因素量化实验，不预设具体原因。\n\n"
    (REPORTS / "reranker_batch_effect.md").write_text(report, encoding="utf-8")
    write_json(directory / "state.json", {"status": "complete", "actual_calls": len(rows), "model_unchanged": True})
    verify_frozen()


if __name__ == "__main__":
    main()
