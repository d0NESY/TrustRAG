import hashlib
import json
from pathlib import Path
import subprocess

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import sha256_file

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/benchmark_v2"
REPORTS = ROOT / "reports/v2"
EXPERIMENTS = ROOT / "experiments/v2"
CORE = ["ragbase/config.py", "ragbase/model.py", "ragbase/schema.py", *[p.relative_to(ROOT).as_posix() for directory in
        ["ingestion", "retrieval", "generation"] for p in sorted((ROOT / "ragbase" / directory).glob("*.py"))],
        "ragbase/evaluation/retrieval_metrics.py", "ragbase/evaluation/generation_metrics.py", "ragbase/evaluation/judge.py"]


def git_commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def protected_files():
    files = []
    for directory in ["experiments", "reports", "configs", "data/benchmark", "data/documents", "data/source"]:
        for path in (ROOT / directory).rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith(("experiments/v2/", "reports/v2/", "configs/v2/", "configs/demo/")) or relative == "reports/human_review_template.csv":
                continue
            files.append(path)
    return sorted(files)


def freeze_v1():
    for directory in [DATA, REPORTS, EXPERIMENTS]:
        directory.mkdir(parents=True, exist_ok=True)
    path = REPORTS / "v1_protection_manifest.json"
    if path.exists():
        return verify_v1()
    manifest = {"v1_delivery_commit": git_commit(), "files": {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in protected_files()},
                "core_algorithm_sha256": {name: sha256_file(ROOT / name) for name in CORE},
                "policy": "V1 predictions, metrics, reports, configs, data and core algorithms must not change."}
    write_json(path, manifest)
    return manifest


def verify_v1():
    manifest = json.loads((REPORTS / "v1_protection_manifest.json").read_text(encoding="utf-8"))
    mismatches = [name for name, digest in {**manifest["files"], **manifest["core_algorithm_sha256"]}.items()
                  if not (ROOT / name).is_file() or sha256_file(ROOT / name) != digest]
    if mismatches:
        raise ValueError(f"V1 protection violation: {mismatches}")
    return manifest


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
