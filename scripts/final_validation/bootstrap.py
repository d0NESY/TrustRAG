"""Paired question bootstrap, plus family-cluster sensitivity analysis."""

from collections import defaultdict
import numpy as np

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import sha256_file
from ragbase.evaluation.retrieval_metrics import score_ranking
from scripts.final_validation.common import ROOT, OUT, REPORTS, prepare, verify_frozen, retrieval, csv_write, table

SEED = 20261006
REPLICATES = 10000
METRICS = ["recall@1", "recall@5", "mrr", "ndcg@5"]
METHODS = ["dense", "dense_reranker", "hybrid_reranker"]
COMPARISONS = [("dense_reranker", "dense"), ("dense_reranker", "hybrid_reranker")]


def paired_differences(left, right, draws):
    left, right = np.asarray(left), np.asarray(right)
    if left.shape != right.shape or left.ndim != 2:
        raise ValueError("Paired arrays must have identical (questions, metrics) shapes")
    return (left - right)[draws].mean(axis=1)


def main():
    prepare()
    runs = {method: retrieval(method) for method in METHODS}
    identities = sorted(identity for identity, row in runs["dense"].items() if row["answerable"])
    if len(identities) != 120:
        raise ValueError("Expected all 120 answerable V2 test questions")
    arrays = {}
    families = defaultdict(list)
    for position, identity in enumerate(identities):
        row = runs["dense"][identity]
        families[row["family_id"]].append(position)
        for method in METHODS:
            other = runs[method][identity]
            if other["gold_chunk_ids"] != row["gold_chunk_ids"] or other["question"] != row["question"]:
                raise ValueError("Unpaired/gold-changed prediction inputs")
    for method in METHODS:
        arrays[method] = np.array([[score_ranking(runs[method][identity]["ranked_chunk_ids"], runs[method][identity]["gold_chunk_ids"])[key] for key in METRICS] for identity in identities])
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(identities), (REPLICATES, len(identities)), dtype=np.int16)
    family_ids = sorted(families)
    if set(map(len, families.values())) != {6}:
        raise ValueError("Family sensitivity weighting requires balanced six-question families")
    family_draws = rng.integers(0, len(family_ids), (REPLICATES, len(family_ids)), dtype=np.int16)
    rows, deltas = [], {}
    for left, right in COMPARISONS:
        delta = arrays[left] - arrays[right]
        family_delta = np.array([delta[families[family]].mean(axis=0) for family in family_ids])
        for unit, distribution in [("paired_question", paired_differences(arrays[left], arrays[right], draws)),
                                   ("paired_family_cluster", family_delta[family_draws].mean(axis=1))]:
            deltas[unit + "__" + left + "__" + right] = distribution
            for column, metric in enumerate(METRICS):
                values = distribution[:, column]
                lower, upper = np.percentile(values, [2.5, 97.5])
                rows.append({"resampling_unit": unit, "comparison": left + " - " + right, "metric": metric,
                             "point_estimate": float(delta[:, column].mean()), "bootstrap_mean": float(values.mean()),
                             "ci95_lower": float(lower), "ci95_upper": float(upper), "p_delta_gt_zero": float((values > 0).mean()),
                             "seed": SEED, "replicates": REPLICATES, "question_count": len(identities), "family_count": len(family_ids)})
    np.savez_compressed(OUT / "bootstrap_replicates.npz", question_draws=draws, family_draws=family_draws, **deltas)
    source_hashes = {method: sha256_file(ROOT / "experiments/v2/test" / method / "retrieval_predictions.jsonl") for method in METHODS}
    write_json(OUT / "bootstrap_provenance.json", {"seed": SEED, "replicates": REPLICATES, "question_ids": identities,
               "family_ids": family_ids, "metrics": METRICS, "source_prediction_sha256": source_hashes,
               "numpy_version": np.__version__, "rng": "numpy.default_rng/PCG64", "replicate_sha256": sha256_file(OUT / "bootstrap_replicates.npz"),
               "method": "Same question-index draws for all methods; bootstrap paired metric differences directly; percentile interval."})
    csv_write(REPORTS / "bootstrap_summary.csv", rows)
    report = "# Paired Bootstrap：V2 test 排序差异\n\n使用全部 120 道 answerable test 问题，固定 seed=20261006、10,000 次有放回抽样。同一次 replicate 所有方法共享问题 ID；直接重算两方法指标差值，不比较两组单独 CI。\n\n"
    report += table(["unit", "comparison", "metric", "point", "bootstrap mean", "95% low", "95% high", "P(delta>0)"],
                    [[row[key] for key in ["resampling_unit", "comparison", "metric", "point_estimate", "bootstrap_mean", "ci95_lower", "ci95_upper", "p_delta_gt_zero"]] for row in rows])
    report += "\n\n解释：interval suggests 当前样本下的差异范围；不构成严格证明。P(delta>0) 是 bootstrap replicate 中正差值的频率，不是传统 p-value 或总体优越性的后验概率。CI 包含 0（含边界为 0）时，不能写显著优于。Recall@5 两种重排方法均饱和，差值区间为零也不能证明所有未来问题完全相同。\n\n问题级 bootstrap 是本任务主分析；另以 20 个家族整组重采样作敏感性分析，保留家族内六道问题相关性。两种区间仍只描述该合成集，不解决作者偏差、预训练泄漏或外部领域泛化。\n\n抽样索引、每次差值和 source prediction SHA256 保存于 experiments/final_validation/bootstrap_replicates.npz 与 bootstrap_provenance.json。正式结果未修改。\n"
    (REPORTS / "bootstrap_report.md").write_text(report, encoding="utf-8")
    verify_frozen()
    print("10,000 paired bootstrap replicates complete; frozen inputs unchanged.")


if __name__ == "__main__":
    main()
