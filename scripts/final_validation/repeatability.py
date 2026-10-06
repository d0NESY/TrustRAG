"""Five randomized-order live runs: reranker stability and latency together."""

from collections import defaultdict
import json
import os
import random
from statistics import mean, stdev

os.environ.setdefault("HF_HUB_OFFLINE", "1")

from ragbase.config import load_config  # noqa: E402
from ragbase.evaluation.artifacts import write_json  # noqa: E402
from ragbase.evaluation.benchmark import read_jsonl, write_jsonl, sha256_file  # noqa: E402
from ragbase.evaluation.retrieval_metrics import latency_metrics  # noqa: E402
from ragbase.ingestion.indexer import build_index  # noqa: E402
from ragbase.retrieval.hybrid import RetrievalPipeline  # noqa: E402
from scripts.final_validation.common import ROOT, OUT, REPORTS, prepare, verify_frozen, retrieval, csv_write  # noqa: E402

METHODS = ["dense_reranker", "hybrid_reranker"]
SEED = 7102026
ROUNDS = 5


def protocol():
    prepare()
    directory = OUT / "repeatability"
    directory.mkdir(exist_ok=True)
    source = {method: retrieval(method) for method in METHODS}
    dense, hybrid = source.values()
    drift = {}
    for identity, row in dense.items():
        if not row["answerable"]:
            continue
        left = {result["chunk_id"]: result["score"] for result in row["results"]}
        right = {result["chunk_id"]: result["score"] for result in hybrid[identity]["results"]}
        drift[identity] = max(abs(left[chunk] - right[chunk]) for chunk in left.keys() & right.keys())
    identities = []
    mandatory = ["v2_parental_requests_version_conflict", "v2_research_data_version_conflict"]
    for category in ["version_conflict", "exact_term", "semantic"]:
        options = sorted([identity for identity in drift if dense[identity]["category"] == category], key=lambda identity: (-drift[identity], identity))
        chosen = [identity for identity in mandatory if identity in options]
        chosen += [identity for identity in options if identity not in chosen][:10 - len(chosen)]
        identities.extend(chosen)
    rng = random.Random(SEED)
    orders = [rng.sample(METHODS, len(METHODS)) for _ in range(ROUNDS)]
    value = {"seed": SEED, "rounds": ROUNDS, "question_ids": sorted(identities), "orders": orders,
             "configs": {method: load_config(ROOT / "configs/v2" / (method + ".yaml")).to_dict() for method in METHODS},
             "source_prediction_sha256": {method: sha256_file(ROOT / "experiments/v2/test" / method / "retrieval_predictions.jsonl") for method in METHODS},
             "model_artifacts_sha256": sha256_file(ROOT / "docs/model_artifacts.json"),
             "selection": "30 answerable diagnostic queries: 10 version, 10 exact-term, 10 semantic; largest saved score drifts, including both observed top1 reversals. Not a random quality sample.",
             "reuse": "Same actual retrieval+rereanking invocations supply both five-repeat stability and randomized-order latency; no cached query embeddings.",
             "warmup": "Two full retrieve calls per method before each timed method block."}
    path = directory / "protocol.json"
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError("Frozen validation protocol changed")
    else:
        write_json(path, value)
    return value, source


def summarize(rows, protocol_value, source):
    scores, ranks = defaultdict(list), defaultdict(list)
    latency = []
    for row in rows:
        for result in row["results"]:
            key = row["method"], row["id"], result["chunk_id"]
            scores[key].append(result["score"])
            ranks[key].append(result["rank"])
    score_rows = [{"method": method, "id": identity, "category": source[method][identity]["category"], "chunk_id": chunk,
                   "repeats": len(values), "score_mean": mean(values), "score_std": stdev(values), "score_range": max(values) - min(values),
                   "min_rank": min(ranks[(method, identity, chunk)]), "max_rank": max(ranks[(method, identity, chunk)]),
                   "rank_unchanged": len(set(ranks[(method, identity, chunk)])) == 1}
                  for (method, identity, chunk), values in sorted(scores.items())]
    csv_write(REPORTS / "reranker_stability.csv", score_rows)
    agreements = []
    for method in METHODS:
        for identity in protocol_value["question_ids"]:
            part = [row for row in rows if row["method"] == method and row["id"] == identity]
            saved = source[method][identity]
            all_pairs = [(a, b) for a in range(len(part)) for b in range(a + 1, len(part))]
            agreements.append({"method": method, "id": identity, "category": saved["category"],
                               "repeats": len(part), "top1_unique_count": len({row["ranked_chunk_ids"][0] for row in part}),
                               "pairwise_top1_agreement": mean(float(part[a]["ranked_chunk_ids"][0] == part[b]["ranked_chunk_ids"][0]) for a, b in all_pairs),
                               "pairwise_full_rank_agreement": mean(float(part[a]["ranked_chunk_ids"] == part[b]["ranked_chunk_ids"]) for a, b in all_pairs),
                               "top1_agreement_with_formal": mean(float(row["ranked_chunk_ids"][0] == saved["ranked_chunk_ids"][0]) for row in part),
                               "full_rank_agreement_with_formal": mean(float(row["ranked_chunk_ids"] == saved["ranked_chunk_ids"]) for row in part)})
    csv_write(REPORTS / "reranker_rank_agreement.csv", agreements)
    for round_number, order in enumerate(protocol_value["orders"], 1):
        for order_position, method in enumerate(order, 1):
            part = [row for row in rows if row["round"] == round_number and row["method"] == method]
            for component in ["retrieval_latency_ms", "reranking_latency_ms", "total_latency_ms"]:
                metric = latency_metrics([row[component] for row in part])
                latency.append({"round": round_number, "method": method, "order_position": order_position, "component": component,
                                "query_count": len(part), "mean_ms": metric["mean_ms"], "p50_ms": metric["p50_ms"], "p95_ms": metric["p95_ms"]})
    csv_write(REPORTS / "latency_repeatability.csv", latency)
    aggregate = []
    for method in METHODS:
        for component in ["retrieval_latency_ms", "reranking_latency_ms", "total_latency_ms"]:
            part = [row for row in latency if row["method"] == method and row["component"] == component]
            for metric in ["mean_ms", "p50_ms", "p95_ms"]:
                values = [row[metric] for row in part]
                aggregate.append({"method": method, "component": component, "round_metric": metric, "runs": len(values),
                                  "mean_across_runs_ms": mean(values), "std_across_runs_ms": stdev(values), "min_ms": min(values), "max_ms": max(values)})
    csv_write(REPORTS / "latency_across_runs.csv", aggregate)
    write_json(REPORTS / "repeatability_summary.json", {"score_rows": len(score_rows), "maximum_score_std": max(row["score_std"] for row in score_rows),
               "maximum_score_range": max(row["score_range"] for row in score_rows), "rank_changed_passages": sum(not row["rank_unchanged"] for row in score_rows),
               "query_agreements": agreements, "latency_across_runs": aggregate, "scope": protocol_value["selection"]})


def main():
    value, source = protocol()
    from ragbase.evaluation.runtime import verify_runtime
    verify_runtime(load_config(ROOT / "configs/v2/dense_reranker.yaml").generation.base_url)
    directory = OUT / "repeatability"
    configs = {method: load_config(ROOT / "configs/v2" / (method + ".yaml")) for method in METHODS}
    index = build_index((ROOT / "data/benchmark_v2/documents").glob("*.pdf"), configs[METHODS[0]], ROOT / ".runtime/indexes_v2")
    try:
        pipelines = {method: RetrievalPipeline(config, index) for method, config in configs.items()}
        for number, order in enumerate(value["orders"], 1):
            for method in order:
                path = directory / f"round_{number}_{method}.jsonl"
                if path.exists():
                    saved = read_jsonl(path)
                    if len(saved) == len(value["question_ids"]):
                        continue
                    raise ValueError("Partial timed method block: archive separately, do not silently mix restarts")
                for identity in value["question_ids"][:2]:
                    pipelines[method].retrieve(source[method][identity]["question"])
                rows = []
                for position, identity in enumerate(value["question_ids"], 1):
                    original = source[method][identity]
                    batch = pipelines[method].retrieve(original["question"])
                    candidates = [result.chunk_id for result in batch.candidates]
                    if candidates != original["candidate_chunk_ids"]:
                        raise ValueError(f"Frozen candidate list differs: {method}/{identity}")
                    rows.append({"round": number, "method": method, "id": identity, "question": original["question"],
                                 "candidate_chunk_ids": candidates, "ranked_chunk_ids": [result.chunk_id for result in batch.results],
                                 "results": [result.to_dict(include_text=False) for result in batch.results],
                                 "retrieval_latency_ms": batch.retrieval_latency_ms, "reranking_latency_ms": batch.reranking_latency_ms,
                                 "total_latency_ms": batch.total_latency_ms})
                    if position % 10 == 0:
                        print(f"Validation repeat {number}/5 {method}: {position}/30", flush=True)
                write_jsonl(path, rows)
                verify_frozen()
        all_rows = [row for number in range(1, ROUNDS + 1) for method in METHODS for row in read_jsonl(directory / f"round_{number}_{method}.jsonl")]
        if len(all_rows) != 300:
            raise ValueError("Incomplete repeats")
        summarize(all_rows, value, source)
        write_json(directory / "state.json", {"status": "complete", "actual_queries": len(all_rows), "rounds": ROUNDS})
    finally:
        index.close()
    verify_frozen()
    print("Five live randomized-order rounds complete; original candidate lists and frozen files verified.")


if __name__ == "__main__":
    main()
