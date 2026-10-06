from pathlib import Path

import pytest

from ragbase.evaluation.benchmark import align_benchmark, read_jsonl, verify_manifest
from ragbase.evaluation.benchmark import write_jsonl
from ragbase.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def test_checked_in_corpus_and_split_hashes():
    manifest = verify_manifest(ROOT)
    assert manifest["answerable"] >= 100
    assert manifest["unanswerable"] >= 30


def test_alignment_requires_real_support_in_correct_source_page():
    row = {"id": "q", "question": "Sick days?", "answerable": True, "answer": "10 days", "evidence_text": "Sick leave: 10 days.", "relevant_documents": ["policy.pdf"], "relevant_pages": [2]}
    chunks = [{"chunk_id": "A", "text": "Sick leave:\n10 days.", "metadata": {"filename": "policy.pdf", "page": 2}}]
    assert align_benchmark([row], chunks)[0]["relevant_chunk_ids"] == ["A"]
    chunks[0]["metadata"]["page"] = 3
    with pytest.raises(ValueError, match="not preserved"):
        align_benchmark([row], chunks)


def test_experiment_configs_have_same_chunking_and_models():
    configs = [load_config(ROOT / "configs" / f"{name}.yaml") for name in ["baseline", "dense_reranker", "bm25", "hybrid", "hybrid_reranker"]]
    assert len({config.chunking for config in configs}) == 1
    assert len({config.embedding_model for config in configs}) == 1
    assert len({config.retrieval.final_top_k for config in configs}) == 1
    assert len(read_jsonl(ROOT / "data/benchmark/dev.jsonl")) == 40


def test_flashrank_numpy_score_is_saved_as_a_json_number(tmp_path):
    import numpy as np

    output = tmp_path / "predictions.jsonl"
    write_jsonl(output, [{"score": np.float32(0.5)}])
    assert read_jsonl(output) == [{"score": 0.5}]
