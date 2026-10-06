from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
import uuid

from langchain_qdrant import Qdrant

from ragbase.config import Config, ExperimentConfig
from ragbase.evaluation.benchmark import read_jsonl, write_jsonl, sha256_file
from ragbase.ingestion.parser import parse_pdfs
from ragbase.ingestion.chunker import chunk_pages
from ragbase.model import create_embeddings


@dataclass
class SharedIndex:
    vector_store: Qdrant
    chunks: list[dict]
    manifest: dict
    path: Path

    def close(self):
        self.vector_store.client.close()


def build_index(paths, config: ExperimentConfig, index_root=None):
    config.validate()
    paths = sorted(map(Path, paths), key=lambda path: path.name)
    if not paths:
        raise ValueError("Provide at least one PDF")
    if len({path.name for path in paths}) != len(paths):
        raise ValueError("Duplicate filenames require explicit renaming before indexing")
    spec = {"corpus": {path.name: sha256_file(path) for path in paths}, "embedding_model": config.embedding_model,
            "chunking": config.to_dict()["chunking"], "parser": "pdfium-page-normalized-v1"}
    fingerprint = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:24]
    index_root = Path(index_root or Config.Path.APP_HOME / ".runtime" / "indexes")
    path = index_root / fingerprint
    path.mkdir(parents=True, exist_ok=True)
    embeddings = create_embeddings(config)
    manifest_path = path / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        chunks = read_jsonl(path / "chunks.jsonl")
        if sha256_file(path / "chunks.jsonl") != manifest["chunks_sha256"]:
            raise ValueError("Saved shared chunk index checksum mismatch")
        store = Qdrant.from_existing_collection(embedding=embeddings, collection_name="documents", path=path / "qdrant")
        return SharedIndex(store, chunks, manifest, path)
    start = time.perf_counter()
    pages = parse_pdfs(paths)
    parsed_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    docs = chunk_pages(pages, config.chunking, embeddings)
    chunk_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    store = Qdrant.from_documents(documents=docs, embedding=embeddings, path=path / "qdrant", collection_name="documents",
                                 ids=[str(uuid.UUID(doc.metadata["chunk_id"][:32])) for doc in docs])
    index_ms = (time.perf_counter() - start) * 1000
    chunks = [{"chunk_id": doc.metadata["chunk_id"], "document_id": doc.metadata["document_id"], "text": doc.page_content, "metadata": doc.metadata} for doc in docs]
    write_jsonl(path / "chunks.jsonl", chunks)
    manifest = {**spec, "index_id": fingerprint, "chunk_count": len(chunks), "page_count": len(pages),
                "chunks_sha256": sha256_file(path / "chunks.jsonl"), "parsing_ms": parsed_ms, "chunking_ms": chunk_ms,
                "indexing_ms": index_ms, "ingestion_ms": parsed_ms + chunk_ms + index_ms}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
    return SharedIndex(store, chunks, manifest, path)
