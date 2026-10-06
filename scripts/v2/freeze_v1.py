import csv
import json

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl
from scripts.v2.common import ROOT, REPORTS, freeze_v1, verify_v1


def main():
    manifest = freeze_v1()
    metrics = {}
    for name in ["dense", "bm25", "dense_reranker", "hybrid", "hybrid_reranker"]:
        metrics[name] = {kind: json.loads((ROOT / "experiments" / name / (kind + "_metrics.json")).read_text()) for kind in ["retrieval", "generation"]}
    off = json.loads((ROOT / "experiments/hybrid_reranker_no_gate/generation_metrics.json").read_text())
    lines = ["# V1 frozen baseline", "", f"V1 delivery commit: `{manifest['v1_delivery_commit']}`. Formal algorithm commit: `eeea01f`. All existing V1 artifacts/configs and inference code are protected by exact byte SHA-256. This file records the existing results without rerunning, relabeling or reinterpreting V1 test.", "", "| V1 method | Recall@1 | Recall@5 | MRR | Mean retrieval + reranking ms |", "| --- | --- | --- | --- | --- |"]
    for name, result in metrics.items():
        metric = result["retrieval"]
        lines.append(f"| {name} | {metric['recall@1']:.4f} | {metric['recall@5']:.4f} | {metric['mrr']:.4f} | {metric['total_latency_ms']['mean_ms']:.1f} |")
    lines += ["", "| V1 gate | End-to-end F1 | FAR | FRR |", "| --- | --- | --- | --- |"]
    for label, metric in [("ON", metrics["hybrid_reranker"]["generation"]), ("OFF", off)]:
        value = metric["answerability"]
        lines.append(f"| {label} | {value['f1']:.4f} | {value['false_answer_rate']:.4f} | {value['false_refusal_rate']:.4f} |")
    lines += ["", "V2 uses separate data/benchmark_v2, experiments/v2 and reports/v2. No V1 test tuning is permitted.", "", "Independent human review status: PENDING_HUMAN_REVIEW. Codex's earlier semantic inspection is not independent human review."]
    (REPORTS / "V1_FROZEN_BASELINE.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    fields = ["question_id", "question", "gold_answer", "model_answer", "retrieved_sources", "citations", "human_correctness",
              "human_groundedness", "human_citation_valid", "human_notes", "review_status"]
    review_path = ROOT / "reports/human_review_template.csv"
    if review_path.exists():
        raise ValueError("Human review template already exists; do not overwrite reviewer input")
    with review_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in read_jsonl(ROOT / "reports/review_samples.jsonl"):
            citations = list(dict.fromkeys(__import__("re").findall(r"\[(S\d+)\]", row["answer"])))
            writer.writerow({"question_id": row["id"], "question": row["question"], "gold_answer": row["gold_answer"], "model_answer": row["answer"],
                             "retrieved_sources": json.dumps(row["sources"], ensure_ascii=False), "citations": json.dumps(citations),
                             "human_correctness": "", "human_groundedness": "", "human_citation_valid": "", "human_notes": "",
                             "review_status": "PENDING_HUMAN_REVIEW"})
    write_json(REPORTS / "human_review_status.json", {"status": "PENDING_HUMAN_REVIEW", "reviewer": None, "template": "reports/human_review_template.csv", "sample_count": 20})
    verify_v1()
    print(f"Protected {len(manifest['files'])} V1 artifacts and {len(manifest['core_algorithm_sha256'])} core files; human review pending.")


if __name__ == "__main__":
    main()
