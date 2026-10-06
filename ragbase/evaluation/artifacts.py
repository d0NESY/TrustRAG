"""Portable experiment artifacts; saved predictions are the metric source of truth."""

from datetime import datetime
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from zoneinfo import ZoneInfo

from ragbase.evaluation.benchmark import json_scalar, sha256_file, write_jsonl

ROOT = Path(__file__).resolve().parents[2]


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False, default=json_scalar) + "\n", encoding="utf-8", newline="\n")


def code_digest():
    digest = hashlib.sha256()
    paths = sorted((ROOT / "ragbase").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_text(encoding="utf-8").encode())
    return digest.hexdigest()


def provenance(config, split, index, benchmark_path):
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except subprocess.CalledProcessError:
        commit, dirty = None, None
    model = ROOT / ".runtime/ollama/model.json"
    model_artifacts = ROOT / "docs/model_artifacts.json"
    return {**config.to_dict(), "git_commit": commit, "working_tree_dirty": dirty, "code_sha256": code_digest(),
            "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(), "split": split,
            "benchmark_sha256": sha256_file(benchmark_path), "corpus_version": "northstar-v1",
            "index": index.manifest, "python": platform.python_version(), "platform": platform.platform(),
            "llm_resolved": json.loads(model.read_text()) if model.exists() else None,
            "model_artifacts": json.loads(model_artifacts.read_text()) if model_artifacts.exists() else None,
            "dependencies": {name: version(name) for name in ["langchain", "qdrant-client", "fastembed", "flashrank", "pypdfium2"]},
            "latency_definition": "Warm models; query embedding, search and fusion in retrieval; cross-encoder timed separately; no cached query embeddings."}


def save_retrieval_run(directory, resolved, aligned, predictions, summary, chunks):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / "config.json", {key: resolved[key] for key in ["name", "embedding_model", "reranker_model", "llm_model", "chunking", "retrieval", "answerability", "generation"]})
    write_json(directory / "resolved_config.json", resolved)
    write_jsonl(directory / "benchmark_aligned.jsonl", aligned)
    write_jsonl(directory / "retrieval_predictions.jsonl", predictions)
    write_jsonl(directory / "chunks.jsonl", chunks)
    write_json(directory / "retrieval_metrics.json", summary)
    (directory / "run.log").write_text(f"{resolved['timestamp']} Actual {resolved['split']} retrieval; {len(predictions)} queries; code={resolved['code_sha256']}; index={resolved['index']['index_id']}\n", encoding="utf-8", newline="\n")
