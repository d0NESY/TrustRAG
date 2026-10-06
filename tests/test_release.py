import pytest

from scripts.release.rerun import safe_output
from scripts.release.common import ROOT


def test_rerun_cannot_write_frozen_or_escape_directories():
    for value in ["experiments/v2", "experiments/final_validation", "experiments/reproduction", "experiments/reproduction/../../v2", "../other"]:
        with pytest.raises(ValueError):
            safe_output(value)
    assert safe_output("experiments/reproduction/fresh_run") == ROOT / "experiments/reproduction/fresh_run"


def test_release_blind_packet_has_no_judge_or_system_label():
    import csv
    from pathlib import Path
    from scripts.release.audit import LABELS
    path = Path(ROOT) / "reports/release/human_audit_blind.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        names = reader.fieldnames
        rows = list(reader)
    assert len(rows) == 28
    assert not any("judge" in name or "condition" in name or "selection_reason" in name for name in names)
    assert all(row[field] in {"", "0", "1", "UNCERTAIN"} for row in rows for field in LABELS)
