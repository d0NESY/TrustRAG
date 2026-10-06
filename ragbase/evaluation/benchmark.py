"""Gold validation and evidence-preserving chunk alignment."""

import hashlib
import json
from pathlib import Path
import re


def normalize(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, allow_nan=False, default=json_scalar) + "\n" for row in rows), encoding="utf-8", newline="\n")


def json_scalar(value):
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def validate_benchmark(rows):
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate benchmark IDs")
    if len({normalize(row["question"]) for row in rows}) != len(rows):
        raise ValueError("Duplicate benchmark questions")
    for row in rows:
        if not isinstance(row["answerable"], bool):
            raise ValueError("answerable must be a boolean")
        if row["answerable"]:
            if not row.get("answer") or not row.get("relevant_documents") or not row.get("relevant_pages") or not row.get("evidence_text"):
                raise ValueError(f"Missing answerable gold evidence: {row['id']}")
        elif row.get("answer") is not None or row.get("relevant_documents") or row.get("relevant_pages") or row.get("relevant_chunk_ids"):
            raise ValueError(f"Unanswerable sample has positive gold: {row['id']}")
    return rows


def align_benchmark(rows, chunks):
    aligned = []
    for row in validate_benchmark(rows):
        row = dict(row)
        gold = []
        if row["answerable"]:
            evidence = normalize(row["evidence_text"])
            for chunk in chunks:
                metadata = chunk.get("metadata", {})
                if metadata.get("filename") and metadata["filename"] not in row["relevant_documents"]:
                    continue
                if metadata.get("page") and metadata["page"] not in row["relevant_pages"]:
                    continue
                if evidence in normalize(chunk["text"]):
                    gold.append(chunk["chunk_id"])
            if not gold:
                raise ValueError(f"Gold evidence was not preserved in any chunk: {row['id']}")
        row["relevant_chunk_ids"] = sorted(set(gold))
        aligned.append(row)
    return aligned


def sha256_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_manifest(root):
    root = Path(root)
    manifest = json.loads((root / "data/benchmark/manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["files"].items():
        if sha256_file(root / name) != digest:
            raise ValueError(f"Corpus/benchmark changed: {name}")
    dev = validate_benchmark(read_jsonl(root / "data/benchmark/dev.jsonl"))
    test = validate_benchmark(read_jsonl(root / "data/benchmark/test.jsonl"))
    if {row["id"] for row in dev} & {row["id"] for row in test}:
        raise ValueError("Dev/test IDs overlap")
    if {normalize(row["question"]) for row in dev} & {normalize(row["question"]) for row in test}:
        raise ValueError("Dev/test questions overlap")
    return manifest
