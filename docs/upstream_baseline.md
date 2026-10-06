# Upstream baseline

- Project: [curiousily/ragbase](https://github.com/curiousily/ragbase)
- Original commit: `5af7b79162329fa0b725b39d1aeeea7eb1e4428b`
- Initial branch: `master`; development branch: `trust-rag`.
- Initial working tree: clean.
- License: MIT; the upstream `LICENSE` and author attribution are retained.
- Source inspection date: 2026-10-06 (Asia/Shanghai).
- No `AGENTS.md` was found in the project or its ancestor directories.

## Architecture confirmed from source

`Streamlit upload -> PyPDFium2Loader -> SemanticChunker -> RecursiveCharacterTextSplitter -> FastEmbed -> local Qdrant -> dense similarity retrieval -> optional FlashRank -> optional LLMChainFilter -> LangChain chat model -> streaming Streamlit UI`

| Module | Existing upstream responsibility |
| --- | --- |
| `app.py` | Upload UI, cached QA chain, chat display, streamed answers, source expanders |
| `ragbase/uploader.py` | Write uploaded PDFs; remove the shared document/index directories by default |
| `ragbase/ingestor.py` | PDF extraction, semantic/recursive chunking, embedding and Qdrant indexing |
| `ragbase/retriever.py` | Dense retrieval and optional contextual compression |
| `ragbase/chain.py` | Context prompt, chat history wrapper, streaming events |
| `ragbase/model.py` | Ollama/Groq, FastEmbed and FlashRank constructors |
| `ragbase/session_history.py` | Process-local chat history dictionary |
| `ragbase/config.py` | Nested configuration constants |

## Original settings

- Python requirement: `>=3.12,<3.13`.
- Embedding: `BAAI/bge-base-en-v1.5`.
- Reranker: `ms-marco-MiniLM-L-12-v2`.
- Ollama model: `gemma2:9b`.
- Groq model: `llama-3.1-70b-versatile`.
- Original default: `USE_LOCAL=False`, reranker enabled, chain filter disabled.
- Semantic split threshold: interquartile.
- Recursive chunk size: 2048 characters; overlap: 128 characters.
- Dense retrieval: similarity, `k=5`.
- Generation temperature: 0; maximum tokens: 8000.
- UI message limit: 6 messages, including the initial greeting.
- Per-file upload limit: 2 MB (`.streamlit/config.toml`).

## Original dependencies

The complete, original dependency resolution remains in `poetry.lock`.

| Dependency | Original `pyproject.toml` constraint |
| --- | --- |
| langchain-community | ^0.2.6 |
| langchain-experimental | ^0.0.62 |
| langchain-qdrant | ^0.1.1 |
| langchain-groq | ^0.1.6 |
| qdrant-client | ^1.10.1 |
| fastembed | ^0.3.3 |
| flashrank | ^0.2.8 |
| pypdfium2 | ^4.30.0 |
| streamlit | ^1.36.0 |
| python-dotenv | ^1.0.1 |

## Observed source limitations

These are source observations, not measured benchmark results.

- Fixed `session-id-42` and a shared history dictionary do not isolate model history between browser sessions.
- Default upload handling removes shared storage directories.
- Combining PDF pages before creating new Documents loses original filename/page metadata.
- History is supplied to generation but the retriever receives only the latest question.
- Sources are expanded below the answer, without claim-level source identifiers.
- Abstention relies on the prompt; there is no calibrated evidence gate.
- No fixed benchmark or evaluation harness is included upstream.

## Planned additions and attribution boundary

The requested TrustRAG additions are BM25 over shared chunk identities, RRF fusion,
controlled reranking comparisons, preserved metadata/source citations, dev-calibrated
answerability, and reproducible evaluation/failure analysis. These have **not yet been
implemented**. Algorithm work must wait until the original end-to-end pipeline has
been reproduced, as required by the user's Phase 0 gate.

PDF ingestion, semantic/recursive splitting, FastEmbed, Qdrant, FlashRank, Streamlit,
local/remote model support and chat history are upstream features, not new contributions.
