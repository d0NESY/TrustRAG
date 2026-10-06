from collections import Counter
import re
from statistics import mean

from ragbase.generation.answerability import answerability_metrics
from ragbase.generation.citation import PATTERN
from ragbase.evaluation.retrieval_metrics import latency_metrics


def answer_tokens(text):
    text = PATTERN.sub("", text or "").casefold()
    tokens = re.findall(r"\w+", text)
    return [token for token in tokens if token not in {"a", "an", "the"}]


def token_f1(answer, reference):
    pred, gold = answer_tokens(answer), answer_tokens(reference)
    shared = sum((Counter(pred) & Counter(gold)).values())
    if not shared:
        return float(not pred and not gold)
    precision, recall = shared / len(pred), shared / len(gold)
    return 2 * precision * recall / (precision + recall)


def generation_metrics(predictions):
    gold = [row["answerable"] for row in predictions]
    decisions = [not row["abstained"] for row in predictions]
    gate = [row["gate"]["sufficient"] for row in predictions]
    correctness, grounded, citation_judge = [], [], []
    correct_refs, total_refs = 0, 0
    for row in predictions:
        judge = row.get("judge", {})
        if row["answerable"]:
            if row["abstained"]:
                correctness.append(0.0)
            elif judge.get("status") == "ok":
                correctness.append(float(judge["answer_correct"]))
        if not row["abstained"]:
            if judge.get("status") == "ok":
                grounded.append(float(judge["grounded"]))
                citation_judge.append(float(judge["citations_supported"]))
            sources = {source["source_id"]: source for source in row["sources"]}
            for source_id in row["citation_validation"]["cited_ids"]:
                total_refs += 1
                source = sources.get(source_id)
                correct_refs += bool(source and source["chunk_id"] in row["gold_chunk_ids"])
    token_scores = [token_f1(row["answer"], row["gold_answer"]) if not row["abstained"] else 0.0 for row in predictions if row["answerable"]]
    result = {"answer_correctness": mean(correctness) if correctness else None,
              "answer_correctness_count": len(correctness), "groundedness": mean(grounded) if grounded else None,
              "groundedness_count": len(grounded), "citation_support_judge": mean(citation_judge) if citation_judge else None,
              "citation_accuracy": correct_refs / total_refs if total_refs else None,
              "correct_gold_source_citations": correct_refs, "total_citations": total_refs,
              "answerability": answerability_metrics(gold, decisions), "retrieval_gate_answerability": answerability_metrics(gold, gate),
              "answer_token_f1": mean(token_scores) if token_scores else None,
              "judge_failure_count": sum(row.get("judge", {}).get("status") == "invalid_output" for row in predictions),
              "raw_invalid_citation_count": sum(bool(row["citation_validation"]["invalid_ids"]) for row in predictions),
              "input_tokens": sum(row["input_tokens"] for row in predictions), "output_tokens": sum(row["output_tokens"] for row in predictions),
              "judge_input_tokens": sum(row.get("judge", {}).get("input_tokens", 0) for row in predictions),
              "judge_output_tokens": sum(row.get("judge", {}).get("output_tokens", 0) for row in predictions),
              "estimated_cost_usd": sum(row["estimated_cost_usd"] for row in predictions if row["estimated_cost_usd"] is not None) if any(row["estimated_cost_usd"] is not None for row in predictions) else None,
              "model": "See resolved_config.json for fixed generator/judge and hardware.",
              "definitions": {"answer_correctness": "LLM judge on answerable questions; refusals count 0; judge errors excluded and counted.",
                              "groundedness": "LLM judge on published answers using only cited source excerpts; fallible.",
                              "citation_accuracy": "Deterministic gold-source citation precision across unique references in published answers; source relevance proxy, not claim entailment.",
                              "citation_support_judge": "Separate semantic claim/source support judgment; fallible.",
                              "answerability": "Positive=published non-abstaining answer; FAR=FP/negative gold, FRR=FN/positive gold.",
                              "input_tokens": "API-reported counts; local Ollama prompt_eval_count can reflect prompt-cache computation.",
                              "estimated_cost_usd": "Configured API token prices only; local compute/electricity is not priced."}}
    for field in ["retrieval_latency_ms", "reranking_latency_ms", "generation_latency_ms", "total_latency_ms", "judge_latency_ms"]:
        result[field] = latency_metrics([row[field] for row in predictions if field in row])
    return result
