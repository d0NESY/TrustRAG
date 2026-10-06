import json
import numpy as np
import pytest

from scripts.final_validation.bootstrap import paired_differences
from scripts.final_validation.external_build import sentence_span


def test_paired_identical_systems_have_zero_uncertainty_even_with_variable_scores():
    values = np.array([[1.0, 0.5], [0.0, 0.0], [1.0, 1.0]])
    draws = np.array([[0, 0, 0], [1, 1, 2], [2, 0, 1]])
    assert not paired_differences(values, values, draws).any()


def test_paired_sampling_preserves_question_correspondence():
    left = np.array([[1.0], [0.0], [0.5]])
    right = np.array([[0.0], [1.0], [0.5]])
    draws = np.array([[0, 1, 2], [0, 0, 2], [1, 1, 2]])
    assert paired_differences(left, right, draws).ravel().tolist() == [0.0, 2 / 3, -2 / 3]
    with pytest.raises(ValueError, match="identical"):
        paired_differences(left, right[:2], draws)


def test_native_gold_offset_mismatch_is_not_silently_repaired():
    text = "First sentence. The fee is five dollars. Last sentence."
    answer = {"text": "five dollars", "answer_start": text.index("five")}
    assert sentence_span(text, answer) == "The fee is five dollars."
    with pytest.raises(ValueError, match="offsets"):
        sentence_span(text, {"text": "six dollars", "answer_start": text.index("five")})


def test_uncertain_human_labels_are_excluded_not_counted_as_errors(tmp_path, monkeypatch):
    from scripts.final_validation import human_audit as audit
    from scripts.final_validation.common import csv_write
    monkeypatch.setattr(audit, "REPORTS", tmp_path)
    monkeypatch.setattr(audit, "verify_frozen", lambda: {})
    rows = []
    samples = []
    for number, label in enumerate(["1", "0", "UNCERTAIN"], 1):
        key = f"fixture_{number}"
        rows.append({"sample_key": key, "question_id": key, "reviewer_id": "unit_test_fixture_only", "human_notes": "",
                     **{field: label for field in audit.LABELS}})
        samples.append({"sample_key": key, "judge": {"status": "not_applicable"}})
    csv_write(tmp_path / "human_audit_template.csv", rows)
    (tmp_path / "human_audit_metadata.json").write_text(json.dumps({"samples": samples}))
    audit.summarize()
    status = json.loads((tmp_path / "human_audit_status.json").read_text())
    assert status["metrics"][0]["value"] == 0.5
    assert status["metrics"][0]["certain_count"] == 2
    assert status["uncertain_rows"] == 1
    assert all(row["comparable_count"] == 0 for row in status["human_vs_judge"])
