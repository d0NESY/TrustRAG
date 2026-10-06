import json
import pytest

from ragbase.config import load_config
from ragbase.evaluation.benchmark import read_jsonl
from scripts.v2.build_benchmark import question_template
from scripts.v2.common import DATA, ROOT, verify_v1
from scripts.v2.diagnostics import rescue_state, first_gold_rank, rank_change, auc_pairwise


def test_v1_protection_and_demo_defaults():
    verify_v1()
    assert load_config(ROOT / "configs/hybrid_reranker.yaml").answerability.enabled
    assert not load_config(ROOT / "configs/demo/hybrid_reranker.yaml").answerability.enabled
    original = load_config(ROOT / "configs/hybrid_reranker.yaml")
    modified = load_config(ROOT / "configs/v2/hybrid_reranker.yaml")
    assert original.retrieval == modified.retrieval
    assert original.chunking == modified.chunking
    for name in ["baseline", "bm25", "dense_reranker", "hybrid", "hybrid_reranker"]:
        demo = load_config(ROOT / "configs/demo" / (name + ".yaml"))
        frozen = load_config(ROOT / "configs" / (name + ".yaml"))
        assert not demo.answerability.enabled
        assert demo.retrieval == frozen.retrieval
        assert demo.chunking == frozen.chunking
        assert demo.generation == frozen.generation


def test_family_split_and_question_integrity():
    dev, test = read_jsonl(DATA / "dev.jsonl"), read_jsonl(DATA / "test.jsonl")
    assert len(dev) == 80 and len(test) == 160
    assert not {row["family_id"] for row in dev} & {row["family_id"] for row in test}
    assert not {question_template(row["question"]) for row in dev} & {question_template(row["question"]) for row in test}
    integrity = json.loads((ROOT / "reports/v2/benchmark_integrity.json").read_text())
    assert integrity["near_duplicate_checks"]["pairs"] == []
    assert sum(row["answerable"] for row in dev + test) == 180
    assert sum(not row["answerable"] for row in dev + test) == 60


def test_rescue_partition_and_censored_rank_delta():
    assert rescue_state(False, True) == "Dense Miss / BM25 Hit"
    assert rescue_state(True, False) == "BM25 Miss / Dense Hit"
    assert rescue_state(True, True) == "Both Hit"
    assert rescue_state(False, False) == "Both Miss"
    assert first_gold_rank(["x", "gold"], ["gold"]) == 2
    missing = first_gold_rank(["x"], ["gold"])
    result = rank_change(missing, 2)
    assert result["gold_rank_before"] is None and result["rank_delta"] == 9
    assert result["classification"] == "Improved"


def test_score_separation_auc_handles_ties():
    assert auc_pairwise([0.8, 0.9], [0.1, 0.2]) == 1
    assert auc_pairwise([0.5], [0.5]) == 0.5
    assert auc_pairwise([], [0.5]) is None


def test_candidate_recall_is_not_any_gold_hit():
    from scripts.v2.analyze import candidate_metrics
    result = candidate_metrics([{"answerable": True, "gold_chunk_ids": ["g1", "g2"], "candidate_chunk_ids": ["g1", "x"]},
                                {"answerable": False, "gold_chunk_ids": [], "candidate_chunk_ids": ["x"]}])
    assert result["candidate_recall"] == 0.5
    assert result["candidate_hit_rate"] == 1.0


def test_diagnostics_reject_partial_and_duplicate_runs(tmp_path, monkeypatch):
    from scripts.v2 import analyze
    from ragbase.evaluation.benchmark import write_jsonl
    monkeypatch.setattr(analyze, "EXPERIMENTS", tmp_path / "runs")
    monkeypatch.setattr(analyze, "DATA", tmp_path / "data")
    directory = tmp_path / "runs/test/dense"
    directory.mkdir(parents=True)
    (tmp_path / "data").mkdir()
    write_jsonl(tmp_path / "data/test.jsonl", [{"id": "first"}, {"id": "second"}])
    state = directory / "run_state.json"
    state.write_text(json.dumps({"state": "started"}))
    with pytest.raises(ValueError, match="Incomplete run"):
        analyze.complete_rows("test", "dense", "retrieval_predictions.jsonl")
    state.write_text(json.dumps({"state": "complete"}))
    write_jsonl(directory / "retrieval_predictions.jsonl", [{"id": "first"}, {"id": "first"}])
    with pytest.raises(ValueError, match="Missing/duplicate"):
        analyze.complete_rows("test", "dense", "retrieval_predictions.jsonl")


def snapshot_fixture(tmp_path, monkeypatch, original_is_clone=False):
    import hashlib
    from zipfile import ZipFile
    from scripts.v2 import byte_snapshot as snapshot
    clone = tmp_path / "clone"
    clone.mkdir()
    files = {"first.py": b"first\n", "second.json": b"{}\n"}
    archive = tmp_path / "snapshot.zip"
    with ZipFile(archive, "w") as stream:
        for name, content in files.items():
            stream.writestr(name, content)
            (clone / name).write_bytes(content.replace(b"\n", b"\r\n"))
    metadata = tmp_path / "snapshot.json"
    metadata.write_text(json.dumps({"original_workspace": str(clone if original_is_clone else tmp_path / "original"),
                                   "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                                   "files": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}}))
    monkeypatch.setattr(snapshot, "ROOT", clone)
    monkeypatch.setattr(snapshot, "ARCHIVE", archive)
    monkeypatch.setattr(snapshot, "METADATA", metadata)
    monkeypatch.setattr(snapshot, "verify_v1", lambda: {})
    return snapshot, clone


def test_byte_restore_refuses_original_workspace(tmp_path, monkeypatch):
    snapshot, clone = snapshot_fixture(tmp_path, monkeypatch, original_is_clone=True)
    with pytest.raises(ValueError, match="original frozen workspace"):
        snapshot.check_or_restore(True)
    assert (clone / "first.py").read_bytes() == b"first\r\n"


def test_byte_restore_only_new_clone_eols(tmp_path, monkeypatch):
    snapshot, clone = snapshot_fixture(tmp_path, monkeypatch)
    snapshot.check_or_restore(True)
    assert (clone / "first.py").read_bytes() == b"first\n"
    assert (clone / "second.json").read_bytes() == b"{}\n"


def test_byte_restore_validates_all_before_writing(tmp_path, monkeypatch):
    snapshot, clone = snapshot_fixture(tmp_path, monkeypatch)
    (clone / "second.json").write_bytes(b'{"changed_metric": 1}\r\n')
    with pytest.raises(ValueError, match="Semantic/binary modification"):
        snapshot.check_or_restore(True)
    assert (clone / "first.py").read_bytes() == b"first\r\n"
