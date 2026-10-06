"""Independent final-validation outputs and immutable V1/V2 inputs."""

import csv
import json
from pathlib import Path

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl, sha256_file
from scripts.v2.common import ROOT, verify_v1, git_commit
from scripts.v2.byte_snapshot import check_or_restore

OUT = ROOT / "experiments/final_validation"
REPORTS = ROOT / "reports/final_validation"


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / "frozen_artifact_manifest.json"
    if not path.exists():
        verify_v1()
        check_or_restore()
        files = {}
        for folder in ["experiments", "reports", "configs", "data/benchmark", "data/documents", "data/source", "data/benchmark_v2", "scripts/v2", "ragbase"]:
            for item in sorted((ROOT / folder).rglob("*")):
                relative = item.relative_to(ROOT).as_posix()
                if item.is_file() and "__pycache__" not in relative and not relative.startswith(("experiments/final_validation/", "reports/final_validation/")) and not relative.endswith(".log"):
                    files[relative] = sha256_file(item)
        for item in [ROOT / "FINAL_REPORT.md", ROOT / "app.py", ROOT / "docs/model_artifacts.json"]:
            files[item.relative_to(ROOT).as_posix()] = sha256_file(item)
        write_json(path, {"frozen_delivery_commit": git_commit(), "files": files,
                          "rule": "No writes to any V1/V2 artifact or inference code; validation is separate."})
    return verify_frozen()


def verify_frozen():
    path = REPORTS / "frozen_artifact_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    changed = [name for name, digest in manifest["files"].items() if not (ROOT / name).is_file() or sha256_file(ROOT / name) != digest]
    if changed:
        raise ValueError(f"Frozen input changes: {changed}")
    verify_v1()
    v2 = json.loads((ROOT / "reports/v2/artifact_verification.json").read_text(encoding="utf-8"))
    changed_v2 = [name for name, digest in v2["experiment_file_sha256"].items() if not (ROOT / name).is_file() or sha256_file(ROOT / name) != digest]
    if changed_v2:
        raise ValueError(f"Original V2 experiment/log changes: {changed_v2}")
    return manifest


def csv_write(path, rows, fields=None):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def table(headers, rows):
    def cell(value):
        return f"{value:.6f}" if isinstance(value, float) else str(value)
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
                      *["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]])


def retrieval(method):
    directory = ROOT / "experiments/v2/test" / method
    if json.loads((directory / "run_state.json").read_text())["state"] != "complete":
        raise ValueError(f"Incomplete formal input: {method}")
    return {row["id"]: row for row in read_jsonl(directory / "retrieval_predictions.jsonl")}
