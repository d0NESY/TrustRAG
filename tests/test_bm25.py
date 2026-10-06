import math

import pytest

from ragbase.retrieval.bm25 import BM25Retriever, tokenize


def chunk(identity, text):
    return {"chunk_id": identity, "document_id": "doc", "text": text, "metadata": {"page": 1}}


def test_bm25_matches_hand_computed_okapi_score_and_identity():
    corpus = [chunk("A", "sick leave sick"), chunk("B", "vacation leave"), chunk("C", "hardware laptop")]
    result = BM25Retriever(corpus).search("sick", 3)
    idf = math.log(1 + (3 - 1 + 0.5) / (1 + 0.5))
    expected = idf * 2 * 2.5 / (2 + 1.5 * (0.25 + 0.75 * 3 / (7 / 3)))
    assert [hit.chunk_id for hit in result] == ["A"]
    assert result[0].score == pytest.approx(expected)
    assert result[0].document_id == "doc"
    assert result[0].metadata["page"] == 1


def test_query_normalization_unknown_terms_and_empty_corpus():
    retriever = BM25Retriever([chunk("A", "AES-256 encryption")])
    assert retriever.search("aes-256", 1)[0].chunk_id == "A"
    assert tokenize("The AES-256") == ["aes-256"]
    assert retriever.search("unsupportedterm", 1) == []
    assert BM25Retriever([]).search("test", 1) == []


def test_duplicate_chunk_ids_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        BM25Retriever([chunk("A", "one"), chunk("A", "two")])
