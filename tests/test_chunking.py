from langchain_core.documents import Document
import pytest

from ragbase.config import ChunkingConfig
from ragbase.ingestion.chunker import chunk_pages


@pytest.mark.parametrize("strategy", ["fixed", "recursive"])
def test_deterministic_identity_offsets_and_page_boundaries(strategy):
    pages = [Document(page_content="Alpha policy sentence. Beta rule follows. " * 4,
                      metadata={"document_id": "doc", "filename": "policy.pdf", "page": page, "source_type": "pdf"}) for page in [1, 2]]
    config = ChunkingConfig(strategy=strategy, chunk_size=70, overlap=12)
    first = chunk_pages(pages, config)
    second = chunk_pages(pages, config)
    assert [doc.metadata["chunk_id"] for doc in first] == [doc.metadata["chunk_id"] for doc in second]
    assert len({doc.metadata["chunk_id"] for doc in first}) == len(first)
    assert {doc.metadata["page"] for doc in first} == {1, 2}
    for doc in first:
        source = pages[doc.metadata["page"] - 1].page_content
        start = doc.metadata["start_index"]
        assert source[start:start + len(doc.page_content)] == doc.page_content
        assert len(doc.page_content) <= 70


def test_overlap_and_missing_semantic_embedding_validation():
    with pytest.raises(ValueError):
        chunk_pages([], ChunkingConfig(chunk_size=10, overlap=10))
    with pytest.raises(ValueError, match="real embeddings"):
        chunk_pages([], ChunkingConfig(strategy="semantic_recursive"))
