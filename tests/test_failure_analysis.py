from ragbase.evaluation.failure_analysis import classify


def row():
    return {"answerable": True, "abstained": False, "gold_chunk_ids": ["gold"], "candidate_chunk_ids": ["gold", "other"],
            "ranked_chunk_ids": ["gold", "other"], "evidence_text": "Sick leave: 10 days.",
            "sources": [{"chunk_id": "gold", "text": "Sick leave: 10 days."}],
            "citation_validation": {"invalid_ids": []},
            "judge": {"status": "ok", "answer_correct": False, "grounded": True, "citations_supported": True}}


def test_supported_wrong_answer_is_not_called_hallucination():
    labels = classify(row())
    assert "Generation Error" in labels
    assert "Generation Hallucination" not in labels
    assert "Retrieval Miss" not in labels


def test_missing_candidate_and_gate_refusal_have_distinct_labels():
    example = row()
    example.update(abstained=True, candidate_chunk_ids=["other"], ranked_chunk_ids=["other"], judge={"status": "not_applicable"})
    labels = classify(example)
    assert "Retrieval Miss" in labels
    assert "False Refusal" in labels
    assert "Generation Hallucination" not in labels
