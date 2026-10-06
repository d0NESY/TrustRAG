"""Shared identities and result types for every retrieval branch."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    document_id: str
    score: float
    rank: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score_type: str = "unknown"
    component_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self, include_text=True):
        result = asdict(self)
        if not include_text:
            result.pop("text")
        return result


@dataclass
class RetrievalBatch:
    results: list[RetrievalResult]
    candidates: list[RetrievalResult]
    retrieval_latency_ms: float
    reranking_latency_ms: float
    total_latency_ms: float
