import hashlib
import json

from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ragbase.config import ChunkingConfig


def chunk_pages(pages, config: ChunkingConfig, embeddings=None):
    if not 0 <= config.overlap < config.chunk_size:
        raise ValueError("Require 0 <= overlap < chunk size")
    recursive = RecursiveCharacterTextSplitter(chunk_size=config.chunk_size, chunk_overlap=config.overlap, add_start_index=True)
    if config.strategy == "semantic_recursive" and embeddings is None:
        raise ValueError("Semantic splitting requires real embeddings")
    semantic = SemanticChunker(embeddings, breakpoint_threshold_type="interquartile") if config.strategy == "semantic_recursive" else None
    chunks = []
    for page in pages:
        text = page.page_content
        parts = []
        if config.strategy == "fixed":
            for start in range(0, len(text), config.chunk_size - config.overlap):
                raw = text[start:start + config.chunk_size]
                stripped = raw.strip()
                if stripped:
                    parts.append((stripped, start + len(raw) - len(raw.lstrip())))
                if start + config.chunk_size >= len(text):
                    break
        elif config.strategy in {"recursive", "semantic_recursive"}:
            semantic_parts = semantic.split_text(text) if semantic else [text]
            cursor = 0
            for semantic_text in semantic_parts:
                semantic_start = text.find(semantic_text, cursor)
                if semantic_start < 0:
                    raise ValueError("Semantic chunk cannot be aligned to normalized page text")
                cursor = semantic_start + len(semantic_text)
                for doc in recursive.create_documents([semantic_text]):
                    start = semantic_start + doc.metadata["start_index"]
                    parts.append((doc.page_content, start))
        else:
            raise ValueError("Unsupported chunking strategy")
        for index, (content, start) in enumerate(parts):
            identity = [page.metadata["document_id"], page.metadata["page"], config.strategy,
                        config.chunk_size, config.overlap, index, start, content]
            chunk_id = hashlib.sha256(json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            metadata = {**page.metadata, "chunk_id": chunk_id, "chunk_index": index, "start_index": start}
            chunks.append(Document(page_content=content, metadata=metadata))
    if len({doc.metadata["chunk_id"] for doc in chunks}) != len(chunks):
        raise ValueError("Duplicate deterministic chunk identities")
    return chunks
