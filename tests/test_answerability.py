import math

import pytest

from ragbase.config import AnswerabilityConfig
from ragbase.generation.answerability import AnswerabilityGate, calibrate, evidence_features, answerability_metrics
from ragbase.schema import RetrievalResult


def result(score):
    return RetrievalResult("A", "doc", score, 1, "evidence")


def test_threshold_is_inclusive_and_empty_evidence_always_refuses():
    gate = AnswerabilityGate(AnswerabilityConfig(enabled=True, threshold=0.5))
    assert gate.decide([result(0.5)]).sufficient
    assert not gate.decide([result(math.nextafter(0.5, 0))]).sufficient
    assert not gate.decide([]).sufficient
    assert not AnswerabilityGate(AnswerabilityConfig(enabled=False)).decide([]).sufficient


def test_feature_values_and_nonfinite_score_rejection():
    assert evidence_features([0.9, 0.6, 0.3])["top3_mean"] == pytest.approx(0.6)
    assert evidence_features([0.9, 0.6])["margin"] == pytest.approx(0.3)
    with pytest.raises(ValueError):
        evidence_features([float("nan")])


def test_calibration_scans_gold_dev_scores_and_selects_perfect_boundary():
    rows = [{"answerable": gold, "results": [{"score": score}]} for gold, score in [(True, 0.9), (True, 0.8), (True, 0.7), (False, 0.6), (False, 0.1)]]
    calibration = calibrate(rows)
    assert calibration["selected_feature"] == "top1"
    assert calibration["threshold"] == 0.7
    assert calibration["selected_metrics"]["f1"] == 1
    with pytest.raises(ValueError, match="AND"):
        calibrate(rows[:3])


def test_false_answer_and_refusal_denominators_are_explicit():
    metrics = answerability_metrics([True, True, False, False], [True, False, True, False])
    assert metrics["f1"] == 0.5
    assert metrics["false_answer_rate"] == 0.5
    assert metrics["false_refusal_rate"] == 0.5
