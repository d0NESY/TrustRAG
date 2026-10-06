from dataclasses import replace
import time

from ragbase.retrieval.bm25 import BM25Retriever
from ragbase.retrieval.dense import DenseRetriever
from ragbase.retrieval.fusion import reciprocal_rank_fusion
from ragbase.retrieval.reranker import CrossEncoderReranker
from ragbase.schema import RetrievalBatch


class RetrievalPipeline:
    def __init__(self, config, index=None, dense=None, sparse=None, reranker=None):
        self.config = config.validate()
        self.dense = dense if dense is not None else (DenseRetriever(index.vector_store) if index is not None else None)
        self.sparse = sparse if sparse is not None else (BM25Retriever(index.chunks, config.retrieval.bm25_k1, config.retrieval.bm25_b) if index is not None else None)
        self.reranker = reranker if reranker is not None else (CrossEncoderReranker(config) if config.retrieval.rerank else None)

    def retrieve(self, query):
        start = time.perf_counter()
        config = self.config.retrieval
        if config.mode == "dense":
            candidates = self.dense.search(query, config.dense_top_k)
        elif config.mode == "bm25":
            candidates = self.sparse.search(query, config.sparse_top_k)
        else:
            dense = self.dense.search(query, config.dense_top_k)
            sparse = self.sparse.search(query, config.sparse_top_k)
            candidates = reciprocal_rank_fusion([dense, sparse], config.rrf_k, config.fusion_top_k)
        retrieval_ms = (time.perf_counter() - start) * 1000
        start_rerank = time.perf_counter()
        if config.rerank:
            results = self.reranker.rerank(query, candidates, config.final_top_k)
            rerank_ms = (time.perf_counter() - start_rerank) * 1000
        else:
            results = [replace(result, rank=rank) for rank, result in enumerate(candidates[:config.final_top_k], 1)]
            rerank_ms = 0.0
        return RetrievalBatch(results=results, candidates=candidates, retrieval_latency_ms=retrieval_ms,
                              reranking_latency_ms=rerank_ms, total_latency_ms=(time.perf_counter() - start) * 1000)
