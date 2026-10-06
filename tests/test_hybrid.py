
from ragbase.config import ExperimentConfig, RetrievalConfig
from ragbase.retrieval.hybrid import RetrievalPipeline
from ragbase.schema import RetrievalResult


class SearchStub:
    def __init__(self, ids):
        self.ids = ids
        self.calls = []

    def search(self, query, k):
        self.calls.append((query, k))
        return [RetrievalResult(identity, "doc", 0.1, rank, identity) for rank, identity in enumerate(self.ids[:k], 1)]


def test_hybrid_uses_same_query_and_deduplicates_shared_identities():
    dense, sparse = SearchStub(["A", "B", "C"]), SearchStub(["C", "A", "D"])
    config = ExperimentConfig(retrieval=RetrievalConfig(mode="hybrid", final_top_k=4, context_top_k=4))
    batch = RetrievalPipeline(config, dense=dense, sparse=sparse).retrieve("same query")
    assert [result.chunk_id for result in batch.results] == ["A", "C", "B", "D"]
    assert dense.calls[0][0] == sparse.calls[0][0] == "same query"
    assert batch.reranking_latency_ms == 0


def test_dense_mode_does_not_invoke_sparse_branch():
    dense, sparse = SearchStub(["A"]), SearchStub(["B"])
    batch = RetrievalPipeline(ExperimentConfig(), dense=dense, sparse=sparse).retrieve("question")
    assert batch.results[0].chunk_id == "A"
    assert sparse.calls == []
