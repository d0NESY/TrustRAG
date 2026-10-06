"""Dev-only controlled chunking and candidate/RRF parameter experiments."""

import argparse
from dataclasses import replace

import yaml

from ragbase.config import load_config
from ragbase.evaluation.artifacts import ROOT, write_json
from ragbase.evaluation.benchmark import verify_manifest
from ragbase.ingestion.indexer import build_index
from scripts.evaluate_retrieval import evaluate

CONFIG_FILES = ["baseline", "dense_reranker", "bm25", "hybrid", "hybrid_reranker"]


def update_configs(chunking=None, retrieval=None):
    for name in CONFIG_FILES:
        path = ROOT / "configs" / f"{name}.yaml"
        config = load_config(path).to_dict()
        if chunking:
            config["chunking"].update(chunking)
        if retrieval:
            config["retrieval"].update(retrieval)
        path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8", newline="\n")


def chunking_ablation():
    base = load_config(ROOT / "configs/baseline.yaml")
    summaries = {}
    for strategy in ["fixed", "recursive", "semantic_recursive"]:
        config = replace(base, name="chunking_" + strategy, chunking=replace(base.chunking, strategy=strategy))
        index = build_index((ROOT / "data/documents").glob("*.pdf"), config)
        try:
            summary = evaluate(config, index, "dev", ROOT / "experiments/chunking" / strategy)
            summaries[strategy] = {**summary, "index_id": index.manifest["index_id"], "chunk_count": index.manifest["chunk_count"]}
        finally:
            index.close()
    preference = {"recursive": 2, "fixed": 1, "semantic_recursive": 0}
    selected = max(summaries, key=lambda strategy: (summaries[strategy]["mrr"], summaries[strategy]["ndcg@5"], summaries[strategy]["hit@5"], preference[strategy]))
    write_json(ROOT / "reports/chunking_ablation.json", {"split": "dev", "objective": "MRR, then nDCG@5 and Hit@5; exact ties prefer recursive, fixed, semantic", "selected": selected, "results": summaries})
    lines = ["# Chunking ablation (dev only)", "", "All other settings are fixed: BGE embedding, dense retrieval, candidate depth 20, saved ranking depth 10, chunk size 2048 and overlap 128. Gold evidence is realigned by exact normalized source span. Models are warm. No test metrics are used for this choice.", "", "| Strategy | Chunks | Recall@5 | MRR | nDCG@5 |", "| --- | --- | --- | --- | --- |"]
    for strategy, summary in summaries.items():
        lines.append(f"| {strategy} | {summary['chunk_count']} | {summary['recall@5']:.4f} | {summary['mrr']:.4f} | {summary['ndcg@5']:.4f} |")
    lines += ["", f"Selected: `{selected}` by the predeclared dev objective."]
    (ROOT / "reports/chunking_ablation.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    update_configs(chunking={"strategy": selected})
    print(f"Dev-selected chunking: {selected}", flush=True)


def retrieval_ablation():
    base = load_config(ROOT / "configs/hybrid_reranker.yaml")
    index = build_index((ROOT / "data/documents").glob("*.pdf"), base)
    summaries = {}
    try:
        for candidates, rrf_k in [(20, 60), (10, 60), (40, 60), (20, 10), (20, 100)]:
            name = f"candidates_{candidates}_rrf_{rrf_k}"
            config = replace(base, name=name, retrieval=replace(base.retrieval, dense_top_k=candidates, sparse_top_k=candidates,
                                                              fusion_top_k=candidates, rrf_k=rrf_k))
            summaries[name] = {**evaluate(config, index, "dev", ROOT / "experiments/retrieval_tuning" / name), "candidates": candidates, "rrf_k": rrf_k}
    finally:
        index.close()
    selected = max(summaries, key=lambda name: (summaries[name]["mrr"], summaries[name]["ndcg@5"], summaries[name]["hit@5"], int(name == "candidates_20_rrf_60"), -summaries[name]["candidates"], -abs(summaries[name]["rrf_k"] - 60)))
    result = summaries[selected]
    update_configs(retrieval={"dense_top_k": result["candidates"], "sparse_top_k": result["candidates"], "fusion_top_k": result["candidates"], "rrf_k": result["rrf_k"]})
    write_json(ROOT / "reports/retrieval_tuning.json", {"split": "dev", "objective": "MRR, nDCG@5, Hit@5; exact ties prefer default 20/60, then smaller candidates", "selected": selected, "results": summaries})
    lines = ["# Candidate and RRF tuning (dev only)", "", "Fixed corpus, chosen chunking, embedding, cross-encoder and saved ranking depth. The small grid changes one factor around the 20/60 default. It is not an exhaustive hyperparameter search.", "", "| Candidates | RRF k | Recall@5 | MRR | nDCG@5 | Mean ms |", "| --- | --- | --- | --- | --- | --- |"]
    for summary in summaries.values():
        lines.append(f"| {summary['candidates']} | {summary['rrf_k']} | {summary['recall@5']:.4f} | {summary['mrr']:.4f} | {summary['ndcg@5']:.4f} | {summary['total_latency_ms']['mean_ms']:.2f} |")
    lines += ["", f"Selected: `{selected}`. No test metrics were inspected."]
    (ROOT / "reports/retrieval_tuning.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Dev-selected retrieval parameters: {selected}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["chunking", "retrieval"], required=True)
    args = parser.parse_args()
    verify_manifest(ROOT)
    (ROOT / "reports").mkdir(exist_ok=True)
    if args.kind == "chunking":
        chunking_ablation()
    else:
        retrieval_ablation()


if __name__ == "__main__":
    main()
