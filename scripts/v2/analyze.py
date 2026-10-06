"""Recompute V2 diagnostics from complete saved predictions; never tune models."""

import argparse
from collections import Counter
import csv
import json
from statistics import mean

from ragbase.config import load_config
from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import normalize, read_jsonl, sha256_file
from ragbase.evaluation.generation_metrics import generation_metrics
from ragbase.evaluation.retrieval_metrics import percentile, retrieval_metrics
from ragbase.generation.answerability import answerability_metrics, evidence_features
from scripts.v2.common import DATA, EXPERIMENTS, REPORTS, ROOT, verify_v1
from scripts.v2.diagnostics import auc_pairwise, first_gold_rank, hit, rank_change, rank_summary, rescue_state
from scripts.v2.evaluate import METHODS, verify_dataset

SPLITS = ["dev", "test"]
GATES = ["G0_prompt_only", "G1_current_v1_gate"]
SCORES = ["top1", "top3_mean", "margin"]


def write_csv(name, rows):
    if not rows:
        raise ValueError(f"No rows for {name}")
    with (REPORTS / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def table(headers, rows):
    def format_cell(value):
        return f"{value:.4f}" if isinstance(value, float) else str(value)
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |",
                      *["| " + " | ".join(format_cell(value) for value in row) + " |" for row in rows]])


def complete_rows(split, method, filename):
    directory = EXPERIMENTS / split / method
    state = json.loads((directory / "run_state.json").read_text(encoding="utf-8"))
    if state["state"] != "complete":
        raise ValueError(f"Incomplete run: {split}/{method}; do not analyze partial data")
    rows = read_jsonl(directory / filename)
    gold = read_jsonl(DATA / (split + ".jsonl"))
    expected = {row["id"]: row for row in gold}
    if len(rows) != len(expected) or {row["id"] for row in rows} != set(expected):
        raise ValueError(f"Missing/duplicate predictions: {split}/{method}")
    for row in rows:
        reference = expected[row["id"]]
        for field in ["question", "answerable", "category", "family_id", "split"]:
            if row[field] != reference[field]:
                raise ValueError(f"Gold mismatch {row['id']}: {field}")
        if row["answerable"] != bool(row["gold_chunk_ids"]):
            raise ValueError(f"Invalid aligned evidence: {row['id']}")
    return rows


def candidate_metrics(rows):
    positives = [row for row in rows if row["answerable"]]
    return {"candidate_depth": 10,
            "candidate_recall": mean(len(set(row["candidate_chunk_ids"]) & set(row["gold_chunk_ids"])) / len(set(row["gold_chunk_ids"])) for row in positives),
            "candidate_hit_rate": mean(float(hit(row)) for row in positives)}


def metric_row(split, method, category, metric):
    return {"split": split, "method": method, "category": category, "answerable_count": metric["answerable_count"],
            **{key: metric[key] for key in ["recall@1", "recall@3", "recall@5", "recall@10", "mrr", "ndcg@5",
                                           "candidate_recall", "candidate_hit_rate"]},
            "candidate_depth": metric["candidate_depth"], "total_count": metric["total_count"],
            "latency_mean_ms": metric["total_latency_ms"]["mean_ms"],
            "latency_p50_ms": metric["total_latency_ms"]["p50_ms"],
            "latency_p95_ms": metric["total_latency_ms"]["p95_ms"]}


def retrieval_analysis():
    runs, overall, breakdown, checks = {}, [], [], []
    for split in SPLITS:
        runs[split] = {}
        for method in METHODS:
            rows = complete_rows(split, method, "retrieval_predictions.jsonl")
            runs[split][method] = {row["id"]: row for row in rows}
            metric = {**retrieval_metrics(rows), **candidate_metrics(rows)}
            saved = json.loads((EXPERIMENTS / split / method / "retrieval_metrics.json").read_text())
            if metric != saved:
                raise ValueError(f"Metric recomputation differs: {split}/{method}")
            overall.append(metric_row(split, method, "all", metric))
            checks.append({"split": split, "method": method, "count": len(rows), "metrics_match": True})
            for category in sorted({row["category"] for row in rows if row["answerable"]}):
                part = [row for row in rows if row["category"] == category]
                breakdown.append(metric_row(split, method, category, {**retrieval_metrics(part), **candidate_metrics(part)}))
    rescue, changes, rrf = [], [], []
    for split in SPLITS:
        for identity, dense in runs[split]["dense"].items():
            if not dense["answerable"]:
                continue
            bm25, hybrid = runs[split]["bm25"][identity], runs[split]["hybrid"][identity]
            d, b, h = hit(dense), hit(bm25), hit(hybrid)
            union = set(dense["candidate_chunk_ids"]) | set(bm25["candidate_chunk_ids"])
            if not set(hybrid["candidate_chunk_ids"]) <= union:
                raise ValueError(f"RRF produced evidence outside branch union: {identity}")
            rescue.append({"split": split, "id": identity, "category": dense["category"], "question": dense["question"],
                           "candidate_depth": 10, "dense_hit": d, "bm25_hit": b, "hybrid_hit": h,
                           "rescue_state": rescue_state(d, b), "hybrid_rescue_vs_dense": h and not d,
                           "hybrid_only_hit_vs_both_branches": h and not d and not b,
                           "union_size": len(union), "union_hit": bool(union & set(dense["gold_chunk_ids"])),
                           "union_recall": len(union & set(dense["gold_chunk_ids"])) / len(set(dense["gold_chunk_ids"]))})
            before, after = first_gold_rank(dense["ranked_chunk_ids"], dense["gold_chunk_ids"]), first_gold_rank(hybrid["ranked_chunk_ids"], dense["gold_chunk_ids"])
            rrf.append({"split": split, "id": identity, "category": dense["category"], "question": dense["question"],
                        "dense_candidate_hit": d, "bm25_candidate_hit": b, "hybrid_candidate_hit": h,
                        "union_hit": bool(union & set(dense["gold_chunk_ids"])),
                        "rrf_dropped_union_gold": bool(union & set(dense["gold_chunk_ids"])) and not h,
                        "hybrid_rescue_vs_dense": h and not d, "hybrid_loss_vs_dense": d and not h,
                        **rank_change(before, after)})
            for base, reranked in [("dense", "dense_reranker"), ("hybrid", "hybrid_reranker")]:
                initial, final = runs[split][base][identity], runs[split][reranked][identity]
                if initial["candidate_chunk_ids"] != final["candidate_chunk_ids"]:
                    raise ValueError(f"Controlled reranker candidate pool differs: {identity}/{base}")
                if set(final["ranked_chunk_ids"]) != set(final["candidate_chunk_ids"]):
                    raise ValueError(f"Reranker changed candidate membership: {identity}/{base}")
                change = rank_change(first_gold_rank(initial["ranked_chunk_ids"], dense["gold_chunk_ids"]),
                                     first_gold_rank(final["ranked_chunk_ids"], dense["gold_chunk_ids"]))
                changes.append({"split": split, "comparison": base + " -> " + reranked, "id": identity,
                                "category": dense["category"], "question": dense["question"], **change})
    rescue_summary, reranker_summary, rrf_summary = [], [], []
    for split in SPLITS:
        categories = ["all", *sorted({row["category"] for row in rescue if row["split"] == split})]
        for category in categories:
            part = [row for row in rescue if row["split"] == split and (category == "all" or row["category"] == category)]
            counts = Counter(row["rescue_state"] for row in part)
            rescue_summary.append({"split": split, "category": category, "count": len(part),
                                   **{state: counts[state] for state in ["Dense Miss / BM25 Hit", "BM25 Miss / Dense Hit", "Both Hit", "Both Miss"]},
                                   "hybrid_rescue_vs_dense": sum(row["hybrid_rescue_vs_dense"] for row in part),
                                   "hybrid_only_hit_vs_both_branches": sum(row["hybrid_only_hit_vs_both_branches"] for row in part),
                                   "raw_union_max_depth": 20, "raw_union_candidate_recall": mean(row["union_recall"] for row in part),
                                   "raw_union_hit_rate": mean(float(row["union_hit"]) for row in part)})
            rrf_part = [row for row in rrf if row["split"] == split and (category == "all" or row["category"] == category)]
            rrf_summary.append({"split": split, "category": category, **rank_summary(rrf_part),
                                **{field: sum(row[field] for row in rrf_part) for field in ["rrf_dropped_union_gold", "hybrid_rescue_vs_dense", "hybrid_loss_vs_dense"]}})
            for comparison in ["dense -> dense_reranker", "hybrid -> hybrid_reranker"]:
                part_changes = [row for row in changes if row["split"] == split and row["comparison"] == comparison and (category == "all" or row["category"] == category)]
                reranker_summary.append({"split": split, "comparison": comparison, "category": category, **rank_summary(part_changes)})
    for filename, rows in [("retrieval_overall.csv", overall), ("retrieval_by_category.csv", breakdown),
                           ("retrieval_rescue_analysis.csv", rescue), ("retrieval_rescue_summary.csv", rescue_summary),
                           ("reranker_rank_changes.csv", changes), ("rrf_rank_changes.csv", rrf)]:
        write_csv(filename, rows)
    result = {"overall": overall, "by_category": breakdown, "rescue": rescue_summary, "reranker": reranker_summary,
              "rrf": rrf_summary, "verification": checks}
    write_json(REPORTS / "retrieval_diagnostics.json", result)
    return result, runs


def score_distribution(runs):
    rows, summaries, histograms = [], [], []
    threshold = load_config(ROOT / "configs/v2/current_gate.yaml").answerability.threshold
    standalone = []
    for split in SPLITS:
        part = [{"split": split, "id": row["id"], "category": row["category"], "answerable": row["answerable"],
                 **evidence_features([result["score"] for result in row["results"]])}
                for row in runs[split]["hybrid_reranker"].values()]
        rows.extend(part)
        metric = answerability_metrics([row["answerable"] for row in part], [row["top1"] >= threshold for row in part])
        standalone.append({"split": split, "threshold": threshold, **metric,
                           "coverage": (metric["tp"] + metric["fp"]) / metric["count"]})
        for feature in SCORES:
            positives = [row[feature] for row in part if row["answerable"]]
            negatives = [row[feature] for row in part if not row["answerable"]]
            lower, upper = min(positives + negatives), max(positives + negatives)
            width = (upper - lower) / 20 if upper > lower else 1.0
            counts = []
            for label, values in [(True, positives), (False, negatives)]:
                buckets = Counter(min(19, int((value - lower) / width)) for value in values)
                counts.append([buckets[index] / len(values) for index in range(20)])
                for index in range(20):
                    histograms.append({"split": split, "feature": feature, "answerable": label, "bin": index,
                                       "lower_inclusive": lower + index * width, "upper": lower + (index + 1) * width,
                                       "upper_inclusive": index == 19, "count": buckets[index], "fraction": buckets[index] / len(values)})
            overlap = sum(min(a, b) for a, b in zip(*counts))
            for label, values in [(True, positives), (False, negatives)]:
                summaries.append({"split": split, "feature": feature, "answerable": label, "count": len(values),
                                  **{f"p{p}": percentile(values, p) for p in [0, 5, 25, 50, 75, 95, 100]},
                                  "mean": mean(values), "auc_positive_higher": auc_pairwise(positives, negatives),
                                  "histogram_overlap_coefficient": overlap})
    write_csv("answerability_scores.csv", rows)
    write_csv("answerability_score_quantiles.csv", summaries)
    write_csv("answerability_score_histograms.csv", histograms)
    result = {"quantiles": summaries, "standalone_gate": standalone,
              "definitions": {"auc": "P(answerable score > unanswerable score) + 0.5 * ties; higher-is-answerable; no threshold selected on V2.",
                              "overlap": "Sum of minimum class-normalized frequencies in 20 equal-width bins on each split/feature range. Descriptive and bin-dependent.",
                              "coverage": "Fraction of queries allowed by gate; distinct from published-answer coverage."}}
    write_json(REPORTS / "answerability_score_distributions.json", result)
    return result


def cross_pool_diagnostics(runs):
    """Observe shared-passage score drift without running or changing a model."""
    score_rows, rank_rows, summaries = [], [], []
    for split in SPLITS:
        for identity, dense in runs[split]["dense_reranker"].items():
            hybrid = runs[split]["hybrid_reranker"][identity]
            shared = set(dense["ranked_chunk_ids"]) & set(hybrid["ranked_chunk_ids"])
            left = {row["chunk_id"]: row for row in dense["results"]}
            right = {row["chunk_id"]: row for row in hybrid["results"]}
            same_pool = set(dense["candidate_chunk_ids"]) == set(hybrid["candidate_chunk_ids"])
            for chunk_id in sorted(shared):
                score_rows.append({"split": split, "id": identity, "category": dense["category"], "answerable": dense["answerable"],
                                   "chunk_id": chunk_id, "filename": left[chunk_id]["metadata"]["filename"],
                                   "page": left[chunk_id]["metadata"]["page"], "gold": chunk_id in dense["gold_chunk_ids"],
                                   "same_candidate_set": same_pool, "dense_pool_score": left[chunk_id]["score"],
                                   "hybrid_pool_score": right[chunk_id]["score"], "score_delta": right[chunk_id]["score"] - left[chunk_id]["score"]})
            if dense["answerable"]:
                change = rank_change(first_gold_rank(dense["ranked_chunk_ids"], dense["gold_chunk_ids"]),
                                     first_gold_rank(hybrid["ranked_chunk_ids"], dense["gold_chunk_ids"]))
                rank_rows.append({"split": split, "id": identity, "category": dense["category"], "question": dense["question"],
                                  "same_candidate_set": same_pool, "shared_chunk_count": len(shared),
                                  "max_shared_score_delta_abs": max(abs(right[chunk_id]["score"] - left[chunk_id]["score"]) for chunk_id in shared),
                                  "hybrid_top_missing_from_dense_candidates": hybrid["ranked_chunk_ids"][0] not in dense["candidate_chunk_ids"],
                                  **change})
        part = [row for row in score_rows if row["split"] == split]
        ranks = [row for row in rank_rows if row["split"] == split]
        summaries.append({"split": split, **rank_summary(ranks), "shared_passage_comparisons": len(part),
                          "shared_score_delta_abs_mean": mean(abs(row["score_delta"]) for row in part),
                          "shared_score_delta_abs_max": max(abs(row["score_delta"]) for row in part),
                          "shared_score_delta_above_1e_6_count": sum(abs(row["score_delta"]) > 1e-6 for row in part),
                          "degraded_cases_with_top_already_in_dense_pool": sum(row["classification"] == "Degraded" and not row["hybrid_top_missing_from_dense_candidates"] for row in ranks)})
    write_csv("reranker_shared_score_changes.csv", score_rows)
    write_csv("reranker_between_pools_rank_changes.csv", rank_rows)
    write_json(REPORTS / "reranker_cross_pool_diagnostics.json", {"summary": summaries,
               "definition": "Saved predictions only; score drift across different candidate batches is observed, not a verified causal mechanism."})
    return summaries


def gate_analysis(runs):
    overall, checks, cases, breakdown = [], [], [], []
    threshold = load_config(ROOT / "configs/v2/current_gate.yaml").answerability.threshold
    for split in SPLITS:
        conditions = {}
        for gate in GATES:
            rows = complete_rows(split, gate, "generation_predictions.jsonl")
            conditions[gate] = {row["id"]: row for row in rows}
            for row in rows:
                retrieval = runs[split]["hybrid_reranker"][row["id"]]
                if row["ranked_chunk_ids"] != retrieval["ranked_chunk_ids"] or row["evidence_features"] != evidence_features([r["score"] for r in retrieval["results"]]):
                    raise ValueError(f"Gate source/feature mismatch: {row['id']}")
                sufficient = bool(retrieval["results"]) and (gate == "G0_prompt_only" or row["evidence_features"]["top1"] >= threshold)
                if row["gate"]["sufficient"] != sufficient or row["gate"]["threshold"] != threshold:
                    raise ValueError(f"Frozen threshold/decision mismatch: {row['id']}")
            metric = generation_metrics(rows)
            metric["coverage"] = mean(float(not row["abstained"]) for row in rows)
            saved = json.loads((EXPERIMENTS / split / gate / "generation_metrics.json").read_text())
            if metric != saved:
                raise ValueError(f"Generation recomputation differs: {split}/{gate}")
            overall.append({"split": split, "condition": gate, **metric})
            checks.append({"split": split, "condition": gate, "count": len(rows), "metrics_match": True})
            for category in sorted({row["category"] for row in rows}):
                part = [row for row in rows if row["category"] == category]
                category_metric = answerability_metrics([row["answerable"] for row in part], [not row["abstained"] for row in part])
                breakdown.append({"split": split, "condition": gate, "category": category, **category_metric,
                                  "coverage": mean(float(not row["abstained"]) for row in part)})
        for identity, g0 in conditions[GATES[0]].items():
            g1 = conditions[GATES[1]][identity]
            cases.append({"split": split, "id": identity, "category": g0["category"], "question": g0["question"], "answerable": g0["answerable"],
                          "g0_abstained": g0["abstained"], "g1_abstained": g1["abstained"],
                          "g0_refusal_reason": g0["refusal_reason"], "g1_refusal_reason": g1["refusal_reason"],
                          "top1": g1["evidence_features"]["top1"], "top3_mean": g1["evidence_features"]["top3_mean"], "margin": g1["evidence_features"]["margin"],
                          "prevented_false_answer": not g0["answerable"] and not g0["abstained"] and g1["abstained"],
                          "added_false_refusal": g0["answerable"] and not g0["abstained"] and g1["abstained"],
                          "score_gate_prevented_false_answer": not g0["answerable"] and not g0["abstained"] and not g1["gate"]["sufficient"],
                          "score_gate_added_false_refusal": g0["answerable"] and not g0["abstained"] and not g1["gate"]["sufficient"],
                          "score_gate_blocked": not g1["gate"]["sufficient"],
                          "same_prompt_for_allowed": g0["prompt_sha256"] == g1["prompt_sha256"] if g1["gate"]["sufficient"] else None,
                          "raw_answer_changed_while_gate_allowed": g1["gate"]["sufficient"] and g0["raw_answer"] != g1["raw_answer"],
                          "gold_source_in_context": bool(set(g1["gold_chunk_ids"]) & {source["chunk_id"] for source in g1["sources"]}),
                          "gold_evidence_exact_in_excerpts": bool(g1["evidence_text"]) and any(normalize(g1["evidence_text"]) in normalize(source["text"]) for source in g1["sources"]),
                          "g0_answer": g0["answer"], "g1_answer": g1["answer"]})
    write_csv("gate_case_changes.csv", cases)
    write_csv("gate_by_category.csv", breakdown)
    write_csv("gate_metrics.csv", [{"split": row["split"], "condition": row["condition"], **row["answerability"], "coverage": row["coverage"],
                                   "answer_correctness_judge": row["answer_correctness"], "answer_correctness_count": row["answer_correctness_count"],
                                   "judge_failure_count": row["judge_failure_count"], "total_p50_ms": row["total_latency_ms"]["p50_ms"],
                                   "total_p95_ms": row["total_latency_ms"]["p95_ms"]} for row in overall])
    result = {"overall": overall, "by_category": breakdown, "verification": checks,
              "paired_changes": {split: {field: sum(row[field] for row in cases if row["split"] == split)
                                          for field in ["prevented_false_answer", "added_false_refusal", "score_gate_prevented_false_answer",
                                                        "score_gate_added_false_refusal", "raw_answer_changed_while_gate_allowed"]} for split in SPLITS},
              "added_false_refusal_context": {split: {field: sum(row[field] for row in cases if row["split"] == split and row["added_false_refusal"])
                                                       for field in ["gold_source_in_context", "gold_evidence_exact_in_excerpts"]} for split in SPLITS}}
    write_json(REPORTS / "gate_diagnostics.json", result)
    return result


def write_retrieval_reports(result):
    headings = ["split", "category", "N", "BM25 rescue", "Dense rescue", "Both Hit", "Both Miss", "Hybrid vs Dense", "Hybrid-only"]
    report = "# V2 Candidate rescue 分析\n\n候选深度 K=10，hit 指至少一个 gold chunk 进入候选池。只统计可回答题。BM25 rescue 指 Dense Miss / BM25 Hit；Dense rescue 为反向条件。\n\n"
    report += table(headings, [[row[k] for k in ["split", "category", "count", "Dense Miss / BM25 Hit", "BM25 Miss / Dense Hit", "Both Hit", "Both Miss", "hybrid_rescue_vs_dense", "hybrid_only_hit_vs_both_branches"]] for row in result["rescue"]])
    report += "\n\nHybrid-only 指两个分支都未命中而 Hybrid 命中；RRF 只重排分支并集，因此在相同 chunk gold 下这个计数必为零。它与 Hybrid 相对 Dense 的 rescue 不是同一概念。\n\n原始 Dense/BM25 并集最多 20 个候选的覆盖率另存 `retrieval_rescue_summary.csv`，仅用于诊断；正式 Hybrid 仍由 RRF 截断为 10，不得把并集覆盖率称为正式 Hybrid Recall@20。逐题记录见 `retrieval_rescue_analysis.csv`。\n"
    (REPORTS / "retrieval_rescue_analysis.md").write_text(report, encoding="utf-8", newline="\n")
    report = "# V2 Reranker 贡献\n\n正 delta=重排前 gold 首次排名减去重排后排名。未进入前 10 的 gold 记为删失值 K+1=11；这不是观测到的第 11 名。同一比较严格验证候选池一致。\n\n"
    report += table(["split", "comparison", "category", "N", "mean delta", "median delta", "% improved", "% degraded"],
                    [[row[k] for k in ["split", "comparison", "category", "count", "mean_rank_improvement", "median_rank_improvement", "improved_percent", "degraded_percent"]] for row in result["reranker"]])
    report += "\n\n逐题记录见 `reranker_rank_changes.csv`；候选缺失不能由当前重排器补回。排名统计反映首个相关 chunk，不等同于生成正确性。\n"
    (REPORTS / "reranker_contribution.md").write_text(report, encoding="utf-8", newline="\n")
    report = "# V2 RRF 覆盖与排序诊断\n\n比较 Dense 与固定 RRF Hybrid；不调 RRF k=60。覆盖增加、覆盖损失和首个 gold 排名变化分别统计，避免把候选扩展与排序混为一个收益。\n\n"
    report += table(["split", "category", "mean rank delta", "improved %", "degraded %", "Hybrid rescue", "Hybrid loss", "Union gold dropped"],
                    [[row[k] for k in ["split", "category", "mean_rank_improvement", "improved_percent", "degraded_percent", "hybrid_rescue_vs_dense", "hybrid_loss_vs_dense", "rrf_dropped_union_gold"]] for row in result["rrf"]])
    report += "\n\n逐题见 `rrf_rank_changes.csv`。Union gold dropped 指 gold 存在于两个分支最多 20 项的并集，但 RRF 的前 10 丢弃了全部 gold。\n"
    (REPORTS / "rrf_diagnostics.md").write_text(report, encoding="utf-8", newline="\n")


def verification(retrieval, gate):
    manifest = verify_v1()
    verify_dataset()
    inputs = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in sorted(EXPERIMENTS.rglob("*")) if path.is_file()}
    result = {"verified_phase": "all" if gate else "retrieval_only", "v2_complete": bool(gate),
              "v1_unchanged": True, "v1_protected_files": len(manifest["files"]), "core_algorithm_files": len(manifest["core_algorithm_sha256"]),
              "v2_dataset_hashes_match": True, "prediction_counts_and_ids_match": True, "metrics_recomputed_exactly": True,
              "retrieval_runs": retrieval["verification"], "generation_runs": gate["verification"] if gate else [],
              "experiment_file_sha256": inputs, "human_review": "PENDING_HUMAN_REVIEW", "no_v2_calibration": True}
    result["diagnostic_source_sha256"] = {name: sha256_file(ROOT / name) for name in
                                         ["scripts/v2/analyze.py", "scripts/v2/diagnostics.py", "scripts/v2/render_report.py"]}
    template_path = ROOT / "reports/human_review_template.csv"
    with template_path.open(encoding="utf-8-sig", newline="") as stream:
        review_rows = list(csv.DictReader(stream))
    fields = ["human_correctness", "human_groundedness", "human_citation_valid", "human_notes"]
    result["human_review_template"] = {"sample_count": len(review_rows), "sha256": sha256_file(template_path),
                                      "all_human_fields_blank": all(not row[field] for row in review_rows for field in fields)}
    result["runtime_environment_sha256"] = sha256_file(REPORTS / "runtime_environment.json") if (REPORTS / "runtime_environment.json").exists() else None
    from scripts.v2.byte_snapshot import ARCHIVE, METADATA, check_or_restore
    if ARCHIVE.exists():
        check_or_restore()
        byte_manifest = json.loads(METADATA.read_text(encoding="utf-8"))
        result["v1_byte_snapshot"] = {"archive_sha256": sha256_file(ARCHIVE), "metadata_sha256": sha256_file(METADATA),
                                      "verified_files": len(byte_manifest["files"]), "all_frozen_bytes_match": True}
    ui_path = REPORTS / "demo_ui_results.json"
    if ui_path.exists():
        ui = json.loads(ui_path.read_text(encoding="utf-8"))
        expected = {"gate_off_demo_answer", "gate_off_prompt_refusal", "gate_off_uploaded_pdf", "clear_history"}
        if len(ui) != 4 or {row["case"] for row in ui} != expected or "Dense + 重排" not in ui[0]["selected_mode"]:
            raise ValueError("Incomplete demo/default-mode verification")
        result["demo_browser_checks"] = {"status": "passed", "cases": len(ui), "url": ui[0]["url"],
                                         "ui_results_sha256": sha256_file(ui_path),
                                         "screenshot_sha256": {path.name: sha256_file(path) for path in sorted((REPORTS / "demo_screenshots").glob("*.png"))}}
    write_json(REPORTS / "artifact_verification.json", result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["retrieval", "all"], default="all")
    args = parser.parse_args()
    verify_v1()
    verify_dataset()
    result, runs = retrieval_analysis()
    result["cross_pool_scores"] = cross_pool_diagnostics(runs)
    write_json(REPORTS / "retrieval_diagnostics.json", result)
    write_retrieval_reports(result)
    scores = score_distribution(runs)
    gate = gate_analysis(runs) if args.phase == "all" else None
    if gate:
        from scripts.v2.render_report import render
        render(result, scores, gate, runs)
    verification(result, gate)
    print(f"V2 {args.phase} diagnostics recomputed from complete predictions; V1 unchanged.")


if __name__ == "__main__":
    main()
