import math

import pytest

from ragbase.evaluation.retrieval_metrics import score_ranking, retrieval_metrics, percentile


def test_hand_computed_recall_mrr_and_ndcg():
    result = score_ranking(["B", "A", "C"], ["A", "C"])
    assert result["recall@1"] == 0
    assert result["recall@3"] == 1
    assert result["mrr"] == 0.5
    assert result["ndcg@5"] == pytest.approx((1 / math.log2(3) + 0.5) / (1 + 1 / math.log2(3)))


def test_duplicate_retrieval_does_not_inflate_recall():
    result = score_ranking(["A", "A", "C"], ["A", "C"])
    assert result["recall@1"] == 0.5
    assert result["recall@3"] == 1
    assert result["mrr"] == 1


def test_unanswerable_gold_is_excluded_but_latency_is_included():
    result = retrieval_metrics([
        {"answerable": True, "ranked_chunk_ids": ["A"], "gold_chunk_ids": ["A"], "total_latency_ms": 10},
        {"answerable": False, "ranked_chunk_ids": ["B"], "gold_chunk_ids": [], "total_latency_ms": 30},
    ])
    assert result["recall@1"] == 1
    assert result["answerable_count"] == 1
    assert result["total_count"] == 2
    assert result["total_latency_ms"]["mean_ms"] == 20


def test_empty_gold_and_percentile_boundaries():
    with pytest.raises(ValueError):
        score_ranking(["A"], [])
    assert percentile([], 95) is None
    assert percentile([1], 95) == 1
    assert percentile([10, 30], 95) == 29
