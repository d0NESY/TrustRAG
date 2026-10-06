import json

import requests

from ragbase.evaluation.artifacts import ROOT
from ragbase.evaluation.benchmark import sha256_file


def verify_runtime(base_url="http://127.0.0.1:11434"):
    manifest = json.loads((ROOT / "docs/model_artifacts.json").read_text(encoding="utf-8"))
    embedding = manifest["embedding"]
    cache = ROOT / ".runtime/fastembed" / ("models--" + embedding["repo"].replace("/", "--"))
    if (cache / "refs/main").read_text().strip() != embedding["revision"]:
        raise ValueError("Embedding cache revision changed; restore pinned artifacts")
    for filename, digest in embedding["files"].items():
        if sha256_file(cache / "snapshots" / embedding["revision"] / filename) != digest:
            raise ValueError("Embedding model checksum changed")
    for filename, digest in manifest["reranker"]["files"].items():
        if sha256_file(ROOT / ".runtime/flashrank" / manifest["reranker"]["name"] / filename) != digest:
            raise ValueError("Reranker model checksum changed")
    response = requests.get(base_url + "/api/tags", timeout=30)
    response.raise_for_status()
    model = next((model for model in response.json()["models"] if model["name"] == manifest["llm"]["name"]), None)
    if not model or model["digest"] != manifest["llm"]["digest"]:
        raise ValueError("Local LLM differs from the recorded benchmark digest")
    version = requests.get(base_url + "/api/version", timeout=30).json()["version"]
    if version != manifest["ollama"]["version"]:
        raise ValueError("Ollama runtime version differs from the recorded benchmark")
    return manifest
