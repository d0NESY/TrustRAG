"""Diagnostic definitions, independent of retrieval implementation."""

from collections import Counter
from statistics import mean, median


def hit(row, field="candidate_chunk_ids"):
    return bool(set(row[field]) & set(row["gold_chunk_ids"]))


def rescue_state(dense_hit, bm25_hit):
    if dense_hit and bm25_hit:
        return "Both Hit"
    if dense_hit:
        return "BM25 Miss / Dense Hit"
    if bm25_hit:
        return "Dense Miss / BM25 Hit"
    return "Both Miss"


def first_gold_rank(ids, gold, depth=10):
    target = set(gold)
    return next((rank for rank, identity in enumerate(ids[:depth], 1) if identity in target), depth + 1)


def rank_change(before, after, depth=10):
    delta = before - after
    return {"gold_rank_before": before if before <= depth else None, "gold_rank_after": after if after <= depth else None,
            "censored_rank_before": before, "censored_rank_after": after, "rank_delta": delta,
            "classification": "Improved" if delta > 0 else ("Degraded" if delta < 0 else "Unchanged")}


def rank_summary(rows):
    changes = [row["rank_delta"] for row in rows]
    counts = Counter(row["classification"] for row in rows)
    return {"count": len(rows), "mean_rank_improvement": mean(changes) if changes else None,
            "median_rank_improvement": median(changes) if changes else None,
            "improved_percent": 100 * counts["Improved"] / max(len(rows), 1),
            "degraded_percent": 100 * counts["Degraded"] / max(len(rows), 1), "counts": dict(counts),
            "definition": "Positive delta=rank improvement. Missing gold is censored at K+1, not an observed rank."}


def auc_pairwise(positive, negative):
    if not positive or not negative:
        return None
    return sum(float(left > right) + 0.5 * float(left == right) for left in positive for right in negative) / (len(positive) * len(negative))
