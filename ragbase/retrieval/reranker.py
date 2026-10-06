from dataclasses import replace

from flashrank import RerankRequest

from ragbase.model import get_ranker


class CrossEncoderReranker:
    def __init__(self, config=None, client=None):
        self.client = client if client is not None else get_ranker(config)

    def rerank(self, query, results, top_k):
        if not results:
            return []
        passages = [{"id": index, "text": result.text} for index, result in enumerate(results)]
        scored = self.client.rerank(RerankRequest(query=query, passages=passages))
        output = []
        for item in scored:
            original = results[item["id"]]
            output.append(replace(original, score=float(item["score"]), score_type="cross_encoder",
                                  component_scores={**original.component_scores, "cross_encoder": float(item["score"])}))
        output.sort(key=lambda result: (-result.score, result.chunk_id))
        return [replace(result, rank=rank) for rank, result in enumerate(output[:top_k], 1)]
