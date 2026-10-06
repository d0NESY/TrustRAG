"""Deterministic binary-relevance retrieval metrics, excluding unanswerable gold."""

import math
from statistics import mean


def percentile(values, percent):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def latency_metrics(values):
    return {"mean_ms": mean(values) if values else None, "p50_ms": percentile(values, 50), "p95_ms": percentile(values, 95), "count": len(values)}


def score_ranking(ranked_ids, gold_ids, ks=(1, 3, 5, 10)):
    gold = set(gold_ids)
    if not gold:
        raise ValueError("Ranking metrics require nonempty relevant gold IDs")
    ranked = list(dict.fromkeys(ranked_ids))
    result = {f"recall@{k}": len(set(ranked[:k]) & gold) / len(gold) for k in ks}
    result.update({f"hit@{k}": float(bool(set(ranked[:k]) & gold)) for k in ks})
    result["mrr"] = next((1 / rank for rank, chunk_id in enumerate(ranked, 1) if chunk_id in gold), 0.0)
    dcg = sum(1 / math.log2(rank + 1) for rank, chunk_id in enumerate(ranked[:5], 1) if chunk_id in gold)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(5, len(gold)) + 1))
    result["ndcg@5"] = dcg / ideal
    return result


def retrieval_metrics(predictions):
    answerable = [row for row in predictions if row["answerable"]]
    scores = [score_ranking(row["ranked_chunk_ids"], row["gold_chunk_ids"]) for row in answerable]
    result = {key: mean(score[key] for score in scores) for key in scores[0]} if scores else {}
    result["answerable_count"] = len(answerable)
    result["total_count"] = len(predictions)
    for field in ("retrieval_latency_ms", "reranking_latency_ms", "total_latency_ms"):
        result[field] = latency_metrics([row[field] for row in predictions if field in row])
    result["definition"] = "Binary chunk relevance; answerable queries only for ranking; unique ranked IDs; latency includes all queries. MRR is truncated at saved ranking depth."
    return result
