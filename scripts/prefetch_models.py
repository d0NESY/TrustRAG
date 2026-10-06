"""Restore the recorded model artifacts using official sources into local caches."""

import json
import os
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "0"

from flashrank import Ranker  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402

from ragbase.evaluation.artifacts import ROOT  # noqa: E402
from ragbase.evaluation.benchmark import sha256_file  # noqa: E402


def main():
    manifest = json.loads((ROOT / "docs/model_artifacts.json").read_text(encoding="utf-8"))
    embedding = manifest["embedding"]
    cache = ROOT / ".runtime/fastembed"
    snapshot = Path(snapshot_download(repo_id=embedding["repo"], revision=embedding["revision"],
                                      allow_patterns=list(embedding["files"]), cache_dir=str(cache)))
    for filename, digest in embedding["files"].items():
        if sha256_file(snapshot / filename) != digest:
            raise ValueError(f"Embedding artifact mismatch: {filename}")
    # FastEmbed 0.3.3 resolves 'main' rather than exposing revision selection.
    # Pin this project-owned cache reference, then use HF_HUB_OFFLINE=1 at runtime.
    reference = cache / ("models--" + embedding["repo"].replace("/", "--")) / "refs/main"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text(embedding["revision"], encoding="utf-8", newline="\n")
    ranker = Ranker(model_name=manifest["reranker"]["name"], cache_dir=str(ROOT / ".runtime/flashrank"))
    for filename, digest in manifest["reranker"]["files"].items():
        if sha256_file(ranker.model_dir / filename) != digest:
            raise ValueError(f"Reranker artifact mismatch: {filename}")
    print("Pinned BGE and FlashRank artifacts verified. Set HF_HUB_OFFLINE=1 for execution.")


if __name__ == "__main__":
    main()
