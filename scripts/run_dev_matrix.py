from ragbase.config import load_config
from ragbase.evaluation.artifacts import ROOT
from ragbase.evaluation.benchmark import verify_manifest
from ragbase.ingestion.indexer import build_index
from scripts.evaluate_retrieval import evaluate


def main():
    verify_manifest(ROOT)
    configs = [load_config(ROOT / "configs" / f"{name}.yaml") for name in ["baseline", "dense_reranker", "bm25", "hybrid", "hybrid_reranker"]]
    assert len({config.chunking for config in configs}) == 1
    index = build_index((ROOT / "data/documents").glob("*.pdf"), configs[0])
    try:
        for config in configs:
            summary = evaluate(config, index, "dev", ROOT / "experiments" / config.name / "dev")
            print(f"{config.name}: Recall@5={summary['recall@5']:.4f}, MRR={summary['mrr']:.4f}", flush=True)
    finally:
        index.close()


if __name__ == "__main__":
    main()
