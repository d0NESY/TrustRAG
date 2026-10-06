"""Reciprocal rank fusion without mixing incompatible raw score scales."""

from dataclasses import replace


def reciprocal_rank_fusion(rankings, k=60, top_k=20):
    if k <= 0 or top_k <= 0:
        raise ValueError("RRF k and top_k must be positive")
    scores, originals, components = {}, {}, {}
    for ranking in rankings:
        seen = set()
        for rank, result in enumerate(ranking, 1):
            if result.chunk_id in seen:
                continue
            seen.add(result.chunk_id)
            originals.setdefault(result.chunk_id, result)
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + 1 / (k + rank)
            components.setdefault(result.chunk_id, {}).update(result.component_scores)
    ids = sorted(scores, key=lambda identity: (-scores[identity], identity))[:top_k]
    return [replace(originals[identity], score=scores[identity], rank=rank, score_type="rrf",
                    component_scores={**components[identity], "rrf": scores[identity]}) for rank, identity in enumerate(ids, 1)]
