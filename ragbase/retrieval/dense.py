from ragbase.schema import RetrievalResult


class DenseRetriever:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(self, query, top_k):
        hits = self.vector_store.similarity_search_with_score(query, k=top_k)
        results = []
        for rank, (doc, score) in enumerate(hits, 1):
            metadata = dict(doc.metadata)
            results.append(RetrievalResult(chunk_id=metadata["chunk_id"], document_id=metadata["document_id"], score=float(score), rank=rank,
                                           text=doc.page_content, metadata=metadata, score_type="dense_cosine", component_scores={"dense_cosine": float(score)}))
        return results
