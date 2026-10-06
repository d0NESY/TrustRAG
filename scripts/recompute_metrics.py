"""Recompute deterministic summaries without rerunning retrieval or generation."""

import argparse

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl, sha256_file
from ragbase.evaluation.generation_metrics import generation_metrics
from ragbase.evaluation.retrieval_metrics import retrieval_metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment")
    args = parser.parse_args()
    from pathlib import Path
    directory = Path(args.experiment)
    for filename, scorer, output in [("retrieval_predictions.jsonl", retrieval_metrics, "retrieval_metrics.json"),
                                     ("generation_predictions.jsonl", generation_metrics, "generation_metrics.json")]:
        path = directory / filename
        if path.exists():
            before = sha256_file(path)
            write_json(directory / output, scorer(read_jsonl(path)))
            assert sha256_file(path) == before
            print(f"Recomputed {output}; prediction SHA-256 unchanged: {before}")


if __name__ == "__main__":
    main()
