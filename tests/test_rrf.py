import pytest

from ragbase.schema import RetrievalResult
from ragbase.retrieval.fusion import reciprocal_rank_fusion


def ranking(ids, score_type):
    return [RetrievalResult(identity, "doc", 999 if score_type == "bm25" else 0.01, rank, identity, score_type=score_type) for rank, identity in enumerate(ids, 1)]


def test_hand_calculated_rrf_order_and_scale_independence():
    results = reciprocal_rank_fusion([ranking(["A", "B", "C"], "dense"), ranking(["C", "A", "D"], "bm25")], k=60, top_k=4)
    assert [result.chunk_id for result in results] == ["A", "C", "B", "D"]
    assert results[0].score == pytest.approx(1 / 61 + 1 / 62)
    assert results[1].score == pytest.approx(1 / 63 + 1 / 61)


def test_duplicates_do_not_vote_twice_and_empty_lists_are_safe():
    results = reciprocal_rank_fusion([ranking(["A", "A"], "dense")])
    assert results[0].score == pytest.approx(1 / 61)
    assert reciprocal_rank_fusion([[], []]) == []
