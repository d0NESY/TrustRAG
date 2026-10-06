"""Record public model revisions/checksums and the local evaluation hardware."""

import json
import platform
import subprocess

import psutil

from ragbase.evaluation.artifacts import ROOT, write_json
from ragbase.evaluation.benchmark import sha256_file


def main():
    cache = ROOT / ".runtime/fastembed/models--qdrant--bge-base-en-v1.5-onnx-q"
    revision = (cache / "refs/main").read_text(encoding="utf-8").strip()
    snapshot = cache / "snapshots" / revision
    ranker = ROOT / ".runtime/flashrank/ms-marco-MiniLM-L-12-v2"
    model = json.loads((ROOT / ".runtime/ollama/model.json").read_text())
    release = json.loads((ROOT / ".runtime/ollama/release.json").read_text())
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], text=True).strip()
    manifest = {"embedding": {"name": "BAAI/bge-base-en-v1.5", "repo": "qdrant/bge-base-en-v1.5-onnx-q", "revision": revision,
                               "files": {path.name: sha256_file(path) for path in sorted(snapshot.iterdir()) if path.is_file()}},
                "reranker": {"name": "ms-marco-MiniLM-L-12-v2", "files": {path.name: sha256_file(path) for path in sorted(ranker.iterdir()) if path.is_file()}},
                "llm": {"name": model["name"], "digest": model["digest"], "details": model["details"]},
                "ollama": {"version": "0.35.1", "asset_digest": release.get("digest"), "asset_url": release["browser_download_url"]},
                "hardware": {"gpu": gpu, "physical_cpu_cores": psutil.cpu_count(logical=False), "logical_cpu_cores": psutil.cpu_count(),
                             "ram_bytes": psutil.virtual_memory().total, "platform": platform.platform(), "processor": platform.processor()}}
    write_json(ROOT / "docs/model_artifacts.json", manifest)
    print("Recorded pinned model revisions, checksums and hardware.")


if __name__ == "__main__":
    main()
