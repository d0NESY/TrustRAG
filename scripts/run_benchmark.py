"""One frozen formal test run, resumable under identical inputs and parameters."""

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil

os.environ["HF_HUB_OFFLINE"] = "1"

from ragbase.config import load_config  # noqa: E402
from ragbase.evaluation.artifacts import ROOT, code_digest, write_json  # noqa: E402
from ragbase.evaluation.benchmark import verify_manifest, sha256_file  # noqa: E402
from ragbase.evaluation.runtime import verify_runtime  # noqa: E402
from ragbase.ingestion.indexer import build_index  # noqa: E402
from scripts.evaluate_retrieval import evaluate as evaluate_retrieval  # noqa: E402
from scripts.evaluate_generation import evaluate as evaluate_generation  # noqa: E402
from scripts.build_reports import build as build_reports  # noqa: E402

FILES = ["baseline", "dense_reranker", "bm25", "hybrid", "hybrid_reranker"]


def state(path):
    return json.loads(path.read_text(encoding="utf-8"))["state"] if path.exists() else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="experiments")
    parser.add_argument("--phase", choices=["all", "retrieval", "generation"], default="all")
    args = parser.parse_args()
    verify_manifest(ROOT)
    configs = [load_config(ROOT / "configs" / f"{name}.yaml") for name in FILES]
    artifacts = verify_runtime(configs[0].generation.base_url)
    if any(config.llm_model != artifacts["llm"]["name"] or config.generation.judge_model != artifacts["llm"]["name"]
           or config.embedding_model != artifacts["embedding"]["name"] or config.reranker_model != artifacts["reranker"]["name"] for config in configs):
        raise ValueError("Formal matrix requires the recorded generator and judge model")
    if len({config.chunking for config in configs}) != 1 or len({config.embedding_model for config in configs}) != 1:
        raise ValueError("Controlled matrix must share chunks and embedding")
    for config in configs:
        calibration = json.loads((ROOT / config.answerability.calibration_file).read_text())
        if calibration["split"] != "dev" or calibration["threshold"] != config.answerability.threshold or calibration["selected_feature"] != config.answerability.feature:
            raise ValueError("Gate differs from saved dev calibration")
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    freeze_path = output_root / "formal_test_freeze.json"
    fingerprint = {"configs": [config.to_dict() for config in configs], "code_sha256": code_digest(),
                   "benchmark_sha256": sha256_file(ROOT / "data/benchmark/test.jsonl"),
                   "model_artifacts_sha256": sha256_file(ROOT / "docs/model_artifacts.json"),
                   "generation_conditions": [config.name for config in configs] + ["hybrid_reranker_no_gate"]}
    if freeze_path.exists():
        if json.loads(freeze_path.read_text()) != fingerprint:
            raise ValueError("Frozen formal test inputs changed; do not tune or overwrite this run")
    else:
        write_json(freeze_path, fingerprint)
    if args.phase in {"all", "retrieval"}:
        index = build_index((ROOT / "data/documents").glob("*.pdf"), configs[0])
        try:
            for config in configs:
                directory = output_root / config.name
                if state(directory / "retrieval_test_run.json") != "complete":
                    evaluate_retrieval(config, index, "test", directory)
        finally:
            index.close()
    if args.phase in {"all", "generation"}:
        for config in configs:
            directory = output_root / config.name
            if state(directory / "retrieval_test_run.json") != "complete":
                raise ValueError("Complete the frozen retrieval phase first")
            if state(directory / "generation_run.json") != "complete":
                evaluate_generation(config, directory)
        base = output_root / "hybrid_reranker"
        ablation = output_root / "hybrid_reranker_no_gate"
        if state(ablation / "generation_run.json") != "complete":
            ablation.mkdir(exist_ok=True)
            no_gate = replace(configs[-1], name="hybrid_reranker_no_gate", answerability=replace(configs[-1].answerability, enabled=False))
            write_json(ablation / "config.json", no_gate.to_dict())
            resolved = json.loads((base / "resolved_config.json").read_text())
            write_json(ablation / "resolved_config.json", {**resolved, **no_gate.to_dict(), "retrieval_reused_from": base.as_posix()})
            for filename in ["retrieval_predictions.jsonl", "retrieval_metrics.json", "benchmark_aligned.jsonl", "chunks.jsonl"]:
                shutil.copyfile(base / filename, ablation / filename)
            evaluate_generation(configs[-1], base, ablation, no_gate=True)
        build_reports(output_root)
    print("Requested frozen benchmark phase complete.", flush=True)


if __name__ == "__main__":
    main()
