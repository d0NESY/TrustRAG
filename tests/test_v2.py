import json

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
