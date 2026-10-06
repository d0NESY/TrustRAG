import argparse
import json
from pathlib import Path

from ragbase.evaluation.artifacts import ROOT, write_json
from ragbase.evaluation.benchmark import read_jsonl
from ragbase.evaluation.failure_analysis import analyze

METHODS = ["dense", "dense_reranker", "bm25", "hybrid", "hybrid_reranker"]


def number(value):
    return "N/A" if value is None else f"{value:.4f}"


def build(output_root):
    root = Path(output_root)
    lines = ["# Formal test comparison", "", "All rows use the frozen 120-question test split (90 answerable, 30 unanswerable), the same corpus/chunking/BGE embedding, ranking depth 10 and generation context depth 5. Each mode uses its own dev-calibrated evidence gate. No test values selected parameters. Original upstream whole-document results are reported separately in docs/original_baseline_results.md.", "", "## Retrieval", "", "| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@5 | Mean ms | P50 ms | P95 ms |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    retrieval, generation = {}, {}
    for name in METHODS:
        directory = root / name
        retrieval[name] = json.loads((directory / "retrieval_metrics.json").read_text())
        generation[name] = json.loads((directory / "generation_metrics.json").read_text())
        metric = retrieval[name]
        values = [metric[key] for key in ["recall@1", "recall@3", "recall@5", "recall@10", "mrr", "ndcg@5"]] + [metric["total_latency_ms"][key] for key in ["mean_ms", "p50_ms", "p95_ms"]]
        lines.append("| " + name + " | " + " | ".join(number(value) for value in values) + " |")
    lines += ["", "## Generation", "", "Correctness and groundedness use a fixed local Gemma 2 9B judge; every raw label is saved and is fallible. Citation accuracy below is deterministic gold-source precision, with semantic support judged separately. Answerability/FAR/FRR use gold booleans and actual published refusals. Different raw score scales are calibrated separately on dev.", "", "| Method | Answer correctness (judge) | Groundedness (judge) | Citation accuracy (gold source) | Citation support (judge) | Answerability F1 | False answer rate | False refusal rate |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, metric in generation.items():
        values = [metric[key] for key in ["answer_correctness", "groundedness", "citation_accuracy", "citation_support_judge"]] + [metric["answerability"][key] for key in ["f1", "false_answer_rate", "false_refusal_rate"]]
        lines.append("| " + name + " | " + " | ".join(number(value) for value in values) + " |")
    ablation_path = root / "hybrid_reranker_no_gate/generation_metrics.json"
    if ablation_path.exists():
        ablation = json.loads(ablation_path.read_text())
        lines += ["", "## Gate ablation", "", "Same Hybrid + Reranker test retrieval predictions, sources, generator and judge; only the evidence gate is disabled. This condition was declared before the test run.", "", "| Gate | Answer correctness | Answerability F1 | False answer rate | False refusal rate |", "| --- | --- | --- | --- | --- |"]
        for label, metric in [("enabled", generation["hybrid_reranker"]), ("disabled", ablation)]:
            values = [metric["answer_correctness"]] + [metric["answerability"][key] for key in ["f1", "false_answer_rate", "false_refusal_rate"]]
            lines.append("| " + label + " | " + " | ".join(number(value) for value in values) + " |")
    lines += ["", "## Performance and cost", "", "Warm query times are measured. Offline judge time is excluded from online total latency and reported separately. Local hardware/model hashes are in docs/model_artifacts.json. Local compute/electricity cost is not estimated.", "", "| Method | Retrieval mean ms | Reranking mean ms | Generation mean ms | Total P50 ms | Total P95 ms | Judge mean ms | Input tokens | Output tokens |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, metric in generation.items():
        values = [metric[key]["mean_ms"] for key in ["retrieval_latency_ms", "reranking_latency_ms", "generation_latency_ms"]] + [metric["total_latency_ms"][key] for key in ["p50_ms", "p95_ms"]] + [metric["judge_latency_ms"]["mean_ms"]]
        lines.append("| " + name + " | " + " | ".join(number(value) for value in values) + f" | {metric['input_tokens']} | {metric['output_tokens']} |")
    (ROOT / "reports/comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    write_json(ROOT / "reports/comparison.json", {"retrieval": retrieval, "generation": generation})
    final = read_jsonl(root / "hybrid_reranker/generation_predictions.jsonl")
    summary = analyze(final, ROOT / "reports")
    write_json(ROOT / "reports/failure_analysis_summary.json", summary)
    print("Saved real comparison tables, failure taxonomy and review samples.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="experiments")
    args = parser.parse_args()
    build(args.output_root)


if __name__ == "__main__":
    main()
