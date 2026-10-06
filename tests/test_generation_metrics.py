import pytest

from ragbase.evaluation.generation_metrics import token_f1, generation_metrics
from ragbase.evaluation.judge import parse_judge_output


def test_token_f1_ignores_articles_and_citation_ids():
    assert token_f1("The line manager. [S1]", "line manager") == 1
    assert token_f1("10 days", "20 days") == 0.5


def test_judge_schema_is_strict_and_json_fences_are_supported():
    result = parse_judge_output('```json\n{"answer_correct":true,"grounded":false,"citations_supported":false,"reason":"unsupported"}\n```')
    assert result["answer_correct"] is True
    with pytest.raises(ValueError, match="boolean"):
        parse_judge_output('{"answer_correct":"true","grounded":false,"citations_supported":false,"reason":"wrong type"}')


def test_refusal_only_negative_population_has_defined_rates_and_no_fake_judge_score():
    row = {"answerable": False, "abstained": True, "gate": {"sufficient": False}, "judge": {"status": "not_applicable"},
           "citation_validation": {"invalid_ids": [], "cited_ids": []}, "sources": [], "gold_chunk_ids": [],
           "answer": "refused", "gold_answer": None, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": None}
    metrics = generation_metrics([row])
    assert metrics["answerability"]["false_answer_rate"] == 0
    assert metrics["answer_correctness"] is None
    assert metrics["groundedness"] is None
    assert metrics["citation_accuracy"] is None
    assert metrics["answer_token_f1"] is None
