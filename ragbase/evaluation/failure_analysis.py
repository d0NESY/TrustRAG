"""Multi-label failure taxonomy; automatic labels remain hypotheses for review."""

from collections import Counter
import csv
from pathlib import Path
import random

from ragbase.evaluation.benchmark import normalize, write_jsonl

CATEGORIES = ["Retrieval Miss", "Ranking Error", "Chunk Boundary Error", "Insufficient Context", "Generation Hallucination",
              "Wrong Citation", "False Refusal", "False Answer", "Generation Error", "Judge Failure"]
EXPLANATIONS = {
    "Retrieval Miss": ("Gold evidence absent from the candidate pool.", "Inspect lexical mismatch and candidate coverage on dev."),
    "Ranking Error": ("Gold candidate is available but outside the generation context depth.", "Inspect reranker order and final context depth on dev."),
    "Chunk Boundary Error": ("Evidence span is not preserved by the chunk boundaries.", "Inspect gold alignment and overlap; no cross-chunk gold cases are labeled in v1."),
    "Insufficient Context": ("A selected gold chunk's quoted excerpt omits the gold span.", "Inspect the context budget and excerpt boundaries on dev."),
    "Generation Hallucination": ("The fixed LLM judge marked a published claim unsupported.", "Manually check the claim/source pair; judge labels are fallible."),
    "Wrong Citation": ("Invalid reference or citation support failure.", "Inspect exact cited source scope and raw versus published output."),
    "False Refusal": ("Answerable gold question received an abstention.", "Inspect evidence score, gate, source coverage and model refusal separately."),
    "False Answer": ("Unanswerable gold question received a published answer.", "Inspect relevance-versus-answerability and missing-entity/exception inference."),
    "Generation Error": ("Incorrect answer despite claims judged grounded.", "Inspect scope, units and whether the response answers the actual question."),
    "Judge Failure": ("Judge output could not be parsed or validated.", "Review saved raw judge output; do not treat it as negative ground truth."),
}


def classify(row, context_top_k=5):
    labels = []
    gold = set(row["gold_chunk_ids"])
    candidates = set(row["candidate_chunk_ids"])
    selected = set(row["ranked_chunk_ids"][:context_top_k])
    if row["answerable"]:
        if row["abstained"]:
            labels.append("False Refusal")
        if not gold & candidates:
            labels.append("Retrieval Miss")
        elif not gold & selected:
            labels.append("Ranking Error")
        if gold & selected and row.get("evidence_text"):
            quoted = [source for source in row["sources"] if source["chunk_id"] in gold]
            if not any(normalize(row["evidence_text"]) in normalize(source["text"]) for source in quoted):
                labels.append("Insufficient Context")
    elif not row["abstained"]:
        labels.append("False Answer")
    judge = row.get("judge", {})
    if not row["abstained"] and judge.get("status") == "ok":
        if not judge["grounded"]:
            labels.append("Generation Hallucination")
        if not judge["citations_supported"]:
            labels.append("Wrong Citation")
        if row["answerable"] and not judge["answer_correct"] and judge["grounded"]:
            labels.append("Generation Error")
    if row["citation_validation"]["invalid_ids"]:
        labels.append("Wrong Citation")
    if judge.get("status") == "invalid_output":
        labels.append("Judge Failure")
    return list(dict.fromkeys(labels))


def analyze(predictions, output_directory, context_top_k=5):
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    cases, counts = [], Counter()
    for row in predictions:
        labels = classify(row, context_top_k)
        if not labels:
            continue
        counts.update(labels)
        retrieval_failure = bool(set(labels) & {"Retrieval Miss", "Ranking Error", "Chunk Boundary Error", "Insufficient Context"})
        stage = "retrieval" if retrieval_failure else ("answerability" if set(labels) <= {"False Refusal", "False Answer"} else "generation/evaluation")
        cases.append({"id": row["id"], "category": "; ".join(labels), "stage": stage, "question": row["question"],
                      "gold_answer": row["gold_answer"], "published_answer": row["answer"], "raw_answer": row["raw_answer"],
                      "refusal_reason": row["refusal_reason"], "confidence": row["gate"]["confidence"], "threshold": row["gate"]["threshold"],
                      "judge_reason": row.get("judge", {}).get("reason", ""), "review_status": "automatic hypothesis; review required"})
    fields = ["id", "category", "stage", "question", "gold_answer", "published_answer", "raw_answer", "refusal_reason", "confidence", "threshold", "judge_reason", "review_status"]
    with (directory / "failure_analysis.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(cases)
    lines = ["# Failure analysis", "", f"Population: {len(predictions)} formal test questions. {len(cases)} questions have at least one automatic failure label. Categories are multi-label: percentages use all questions and can sum above 100%. LLM-derived labels are hypotheses, not verified human ground truth.", "", "| Category | Count | Percentage | Possible cause | Review / improvement |", "| --- | --- | --- | --- | --- |"]
    for category in CATEGORIES:
        cause, improvement = EXPLANATIONS[category]
        lines.append(f"| {category} | {counts[category]} | {100 * counts[category] / max(len(predictions), 1):.2f}% | {cause} | {improvement} |")
    lines += ["", "## Representative cases", ""]
    for case in cases[:12]:
        lines += [f"- `{case['id']}` — {case['category']} ({case['stage']})", f"  Question: {case['question']}",
                  f"  Gold: {case['gold_answer']}; output: {case['published_answer']}",
                  f"  Gate: {case['confidence']:.8g} / {case['threshold']}; reason: {case['refusal_reason']}"]
    lines += ["", "V1 contains single-page fact gold; zero chunk-boundary labels do not establish robustness to cross-page or multi-hop evidence. Review the prepared sample pack independently before treating model-judge labels as ground truth."]
    (directory / "failure_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    failures = {case["id"] for case in cases}
    chosen = [row for row in predictions if row["id"] in failures][:12]
    controls = [row for row in predictions if row["id"] not in {sample["id"] for sample in chosen}]
    random.Random(42).shuffle(controls)
    chosen += controls[:max(0, 20 - len(chosen))]
    write_jsonl(directory / "review_samples.jsonl", [{"id": row["id"], "question": row["question"], "answerable": row["answerable"],
                                                     "gold_answer": row["gold_answer"], "answer": row["answer"], "raw_answer": row["raw_answer"],
                                                     "gate": row["gate"], "sources": row["sources"], "judge": row["judge"],
                                                     "automatic_categories": classify(row, context_top_k), "independent_human_review": "pending"} for row in chosen])
    return {"question_count": len(predictions), "failure_question_count": len(cases), "category_counts": dict(counts)}
