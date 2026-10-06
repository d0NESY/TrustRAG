"""Read-only metric verification and typed SHA manifest for the release."""

import argparse
import json

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl, sha256_file
from ragbase.evaluation.retrieval_metrics import retrieval_metrics
from ragbase.evaluation.generation_metrics import generation_metrics
from scripts.release.common import ROOT, RELEASE, begin, verify, now


def artifact_type(name):
    if name.endswith(".py"):
        return "code"
    if "prediction" in name or "judge_results" in name:
        return "prediction"
    if "metrics" in name or "bootstrap" in name or "stability" in name or "latency" in name:
        return "metric_or_statistical_evidence"
    if "benchmark" in name or "/documents/" in name or "questions.jsonl" in name:
        return "benchmark_or_source"
    if "config" in name:
        return "configuration"
    if name.endswith(".md") or "human_audit" in name:
        return "documentation_or_audit"
    return "provenance_or_artifact"


def recompute():
    checks = []
    for folder in [ROOT / "experiments", ROOT / "experiments/v2", ROOT / "experiments/final_validation/external/retrieval_only"]:
        if folder.name == "retrieval_only":
            directories = [folder]
        elif folder.name == "v2":
            directories = [item for split in ["dev", "test"] for item in (folder / split).iterdir() if item.is_dir()]
        else:
            directories = [folder / name for name in ["dense", "dense_reranker", "bm25", "hybrid", "hybrid_reranker", "hybrid_reranker_no_gate"]]
        for directory in directories:
            for stem, function in [("retrieval", retrieval_metrics), ("generation", generation_metrics)]:
                path, metrics = directory / (stem + "_predictions.jsonl"), directory / (stem + "_metrics.json")
                if not path.exists() or not metrics.exists():
                    continue
                rows = read_jsonl(path)
                expected = json.loads(metrics.read_text(encoding="utf-8"))
                current = function(rows)
                differences = [key for key in current if current[key] != expected.get(key)]
                if differences:
                    raise ValueError(f"Frozen metric mismatch: {directory}/{stem}: {differences}")
                checks.append({"prediction_path": path.relative_to(ROOT).as_posix(), "count": len(rows), "metrics_match": True,
                               "prediction_sha256": sha256_file(path), "no_model_calls": True})
    from scripts.final_validation.report import verify_bootstrap
    verify_bootstrap()
    write_json(RELEASE / "recompute_verification.json", {"timestamp": now(), "checks": checks, "bootstrap_arrays_recomputed": True,
               "outputs": "Only this release report written; frozen prediction/metric files were read-only."})
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recompute", action="store_true")
    args = parser.parse_args()
    baseline = begin()
    checks = recompute() if args.recompute else []
    entries = []
    for name, original in baseline["entries"].items():
        path = ROOT / name
        digest = sha256_file(path)
        mutable_doc = name in baseline["allowed_updates"]
        entries.append({"path": name, "size": path.stat().st_size, "sha256": digest, "artifact_type": artifact_type(name),
                        "frozen_or_new": "new_authorized_documentation_revision" if mutable_doc else "frozen",
                        "baseline_sha256": original["sha256"], "matches_original_hash": digest == original["sha256"],
                        "authorized_update": mutable_doc})
    known = set(baseline["entries"])
    paths = [ROOT / name for name in ["FINAL_PROJECT_REPORT.md", "REPRODUCE.md", "docs/final_resume_claims_engineering.md", "docs/project_pitch.md", "docs/project_defense_qa.md", "tests/test_release.py"]]
    paths += [path for folder in [RELEASE, ROOT / "scripts/release", ROOT / "experiments/final_validation/external_generation"] if folder.exists() for path in folder.rglob("*") if path.is_file()]
    for path in sorted(set(paths)):
        if not path.is_file() or "__pycache__" in path.as_posix() or path.name in {"final_artifact_manifest.json", "release_commit_receipt.json"} or path.suffix == ".log":
            continue
        name = path.relative_to(ROOT).as_posix()
        if name in known:
            continue
        entries.append({"path": name, "size": path.stat().st_size, "sha256": sha256_file(path), "artifact_type": artifact_type(name),
                        "frozen_or_new": "new", "baseline_sha256": None, "matches_original_hash": None, "authorized_update": False})
    verify()
    write_json(RELEASE / "final_artifact_manifest.json", {"timestamp": now(), "release_baseline_head": baseline["baseline_head"],
               "frozen_artifacts_unchanged": True, "authorized_documentation_revisions": baseline["allowed_updates"],
               "entries": entries, "recomputed_runs": len(checks),
               "self_exclusion": "Manifest and final commit receipt excluded to avoid circular hashes; live runtime logs excluded."})
    print(f"Read-only release verification passed: {sum(e['frozen_or_new']=='frozen' for e in entries)} frozen files, {len(checks)} metric sets recomputed.")


if __name__ == "__main__":
    main()
