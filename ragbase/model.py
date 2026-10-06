from functools import lru_cache

from flashrank import Ranker
from langchain_community.chat_models import ChatOllama
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.language_models import BaseLanguageModel
from langchain_groq import ChatGroq

from ragbase.config import Config, ExperimentConfig


def create_llm(config: ExperimentConfig | None = None) -> BaseLanguageModel:
    if config is not None:
        config.validate()
        if config.generation.provider == "ollama":
            return ChatOllama(model=config.llm_model, base_url=config.generation.base_url,
                              temperature=config.generation.temperature, num_predict=config.generation.max_tokens,
                              num_ctx=config.generation.context_size, keep_alive="1h")
        return ChatGroq(model_name=config.llm_model, temperature=config.generation.temperature,
                        max_tokens=config.generation.max_tokens)
    if Config.Model.USE_LOCAL:
        return ChatOllama(
            model=Config.Model.LOCAL_LLM,
            temperature=Config.Model.TEMPERATURE,
            keep_alive="1h",
            max_tokens=Config.Model.MAX_TOKENS,
        )
    else:
        return ChatGroq(
            temperature=Config.Model.TEMPERATURE,
            model_name=Config.Model.REMOTE_LLM,
            max_tokens=Config.Model.MAX_TOKENS,
        )


@lru_cache(maxsize=4)
def _embeddings(model_name: str, threads: int, cache_dir: str):
    return FastEmbedEmbeddings(model_name=model_name, threads=threads, cache_dir=cache_dir)


def create_embeddings(config: ExperimentConfig | None = None) -> FastEmbedEmbeddings:
    config = config or ExperimentConfig()
    return _embeddings(config.embedding_model, config.embedding_threads, str(Config.Path.APP_HOME / ".runtime" / "fastembed"))


@lru_cache(maxsize=4)
def _ranker(model_name: str, cache_dir: str):
    return Ranker(model_name=model_name, cache_dir=cache_dir)


def get_ranker(config: ExperimentConfig | None = None):
    config = config or ExperimentConfig()
    return _ranker(config.reranker_model, str(Config.Path.APP_HOME / ".runtime" / "flashrank"))


def create_reranker(config: ExperimentConfig | None = None) -> FlashrankRerank:
    return FlashrankRerank(client=get_ranker(config), model=(config.reranker_model if config else Config.Model.RERANKER),
                          top_n=(config.retrieval.final_top_k if config else 3))
