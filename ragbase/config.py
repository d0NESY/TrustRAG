import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import yaml


class Config:
    class Path:
        APP_HOME = Path(os.getenv("APP_HOME", Path(__file__).parent.parent))
        DATABASE_DIR = APP_HOME / "docs-db"
        DOCUMENTS_DIR = APP_HOME / "tmp"
        IMAGES_DIR = APP_HOME / "images"

    class Database:
        DOCUMENTS_COLLECTION = "documents"

    class Model:
        EMBEDDINGS = "BAAI/bge-base-en-v1.5"
        RERANKER = "ms-marco-MiniLM-L-12-v2"
        LOCAL_LLM = "gemma2:9b"
        REMOTE_LLM = "llama-3.1-70b-versatile"
        TEMPERATURE = 0.0
        MAX_TOKENS = 8000
        USE_LOCAL = True

    class Retriever:
        USE_RERANKER = True
        USE_CHAIN_FILTER = False

    DEBUG = False
    CONVERSATION_MESSAGES_LIMIT = 6


@dataclass(frozen=True)
class ChunkingConfig:
    strategy: str = "semantic_recursive"
    chunk_size: int = 2048
    overlap: int = 128


@dataclass(frozen=True)
class RetrievalConfig:
    mode: str = "dense"
    rerank: bool = False
    dense_top_k: int = 20
    sparse_top_k: int = 20
    fusion_top_k: int = 20
    final_top_k: int = 10
    context_top_k: int = 5
    rrf_k: int = 60
    bm25_k1: float = 1.5
    bm25_b: float = 0.75


@dataclass(frozen=True)
class AnswerabilityConfig:
    enabled: bool = False
    threshold: float | None = None
    feature: str = "top1"
    calibration_file: str | None = None


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float = 0.0
    max_tokens: int = 192
    context_size: int = 4096
    seed: int = 42
    provider: str = "ollama"
    base_url: str = "http://127.0.0.1:11434"
    context_chars_per_source: int = 1024
    judge_model: str = "gemma2:9b"
    judge_max_tokens: int = 128
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None


@dataclass(frozen=True)
class ExperimentConfig:
    name: str = "dense"
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    reranker_model: str = "ms-marco-MiniLM-L-12-v2"
    llm_model: str = "gemma2:9b"
    embedding_threads: int = 4
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    answerability: AnswerabilityConfig = field(default_factory=AnswerabilityConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)

    def to_dict(self):
        return asdict(self)

    def validate(self):
        if self.chunking.strategy not in {"fixed", "recursive", "semantic_recursive"}:
            raise ValueError("Unsupported chunking strategy")
        if not 0 <= self.chunking.overlap < self.chunking.chunk_size:
            raise ValueError("Require 0 <= overlap < chunk_size")
        if self.retrieval.mode not in {"dense", "bm25", "hybrid"}:
            raise ValueError("Unsupported retrieval mode")
        for key in ("dense_top_k", "sparse_top_k", "fusion_top_k", "final_top_k", "context_top_k", "rrf_k"):
            if getattr(self.retrieval, key) <= 0:
                raise ValueError(f"{key} must be positive")
        if self.retrieval.context_top_k > self.retrieval.final_top_k:
            raise ValueError("context_top_k must not exceed final_top_k")
        if not 0 <= self.retrieval.bm25_b <= 1 or self.retrieval.bm25_k1 <= 0:
            raise ValueError("Invalid BM25 parameters")
        if self.answerability.feature not in {"top1", "top3_mean", "margin"}:
            raise ValueError("Unsupported evidence feature")
        if self.answerability.enabled and self.answerability.threshold is None:
            raise ValueError("Enabled gate requires a dev-calibrated threshold")
        if self.generation.provider not in {"ollama", "groq"}:
            raise ValueError("Unsupported generation provider")
        if self.generation.max_tokens <= 0 or self.generation.context_size <= 0:
            raise ValueError("Generation token limits must be positive")
        return self


def _construct(cls, data):
    if not isinstance(data, dict):
        raise ValueError(f"{cls.__name__} must be a mapping")
    unknown = set(data) - {f.name for f in fields(cls)}
    if unknown:
        raise ValueError(f"Unknown {cls.__name__} keys: {sorted(unknown)}")
    return cls(**data)


def load_config(path: str | Path) -> ExperimentConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a mapping")
    data = dict(data)
    for key, cls in {"chunking": ChunkingConfig, "retrieval": RetrievalConfig, "answerability": AnswerabilityConfig, "generation": GenerationConfig}.items():
        data[key] = _construct(cls, data.get(key, {}))
    return _construct(ExperimentConfig, data).validate()
