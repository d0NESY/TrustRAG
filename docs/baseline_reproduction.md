# Baseline reproduction log

Status: **passed**. The original upload-to-answer UI pipeline was exercised with a
real local Gemma 2 9B model before algorithm changes.

## Initial environment (2026-10-06, Asia/Shanghai)

- Upstream commit: `5af7b79162329fa0b725b39d1aeeea7eb1e4428b`.
- OS: Windows; shell: PowerShell.
- Python: 3.12.7 (`D:\anaconda\python.exe`).
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB VRAM.
- A project-local `.venv` was created using `python -m venv .venv`.
- Poetry and Ollama are not available on PATH or in the checked default Ollama installation locations.
- Ollama `http://127.0.0.1:11434/api/tags` was unavailable.
- No project `.env` or process-level `GROQ_API_KEY` was present. No secret values were read or logged.
- The base environment has Streamlit 1.37.1 but lacks the upstream RAG dependencies.

## Intended reproduction configuration

- Dependency installation: original Poetry lock export in an isolated environment, with the Windows compatibility exception below.
- Preferred LLM: local Ollama `gemma2:9b`.
- Embedding: `BAAI/bge-base-en-v1.5` (unchanged upstream model).
- Reranker: `ms-marco-MiniLM-L-12-v2` (unchanged upstream model).
- Test PDF: `data/baseline/fictional_handbook.pdf`, three pages of openly fictional company policies. Text extraction and rendered page layout were verified.
- Launch command: `.venv\Scripts\python.exe -m streamlit run scripts/baseline_app.py --server.headless=true --server.address=127.0.0.1 --server.port=8501 --browser.gatherUsageStats=false`.
- The wrapper selects upstream-supported local LLM mode and isolates index/document/model caches in `.runtime`. It does not change upstream retrieval, chunking, prompt or history algorithms.
- Ollama: official portable Windows release 0.35.1; the official release asset SHA-256 was checked during extraction. Service listens only at `127.0.0.1:11434`.
- Actual three-question results: `docs/baseline_ui_results.json`; screenshots in `docs/baseline_screenshots/`; installed versions and resolved LLM digest in `docs/baseline_environment.json`.

## Windows dependency compatibility

`poetry install --only main --no-interaction` failed while building upstream-locked
PyStemmer 2.2.0.1: Microsoft Visual C++ 14.0 or greater was required. That version
does not publish a CPython 3.12 Windows wheel. During Phase 0, the original
`pyproject.toml` and `poetry.lock` were retained unchanged. Runtime dependencies were exported from the
original lock into `docs/baseline_windows_requirements.txt`; only PyStemmer was
changed to 2.2.0.3, which publishes the required official wheel and satisfies the
upstream FastEmbed dependency range. Installation then succeeded.

The later TrustRAG project updates its own dependency declarations/lock for the
Windows wheel and evaluation tools. The exact original dependency files remain
recoverable in the archived upstream commit, rather than being confused with the
updated TrustRAG environment.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple poetry==1.8.5 reportlab==4.2.5 playwright==1.51.0
.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple -r docs/baseline_windows_requirements.txt chardet==5.2.0
```

Poetry version verified: 1.8.5. The host's default pip mirror did not return the
requested packages; the official PyPI index worked. This is a platform-compatible
reproduction, not a claim that the unmodified original lock installs on Windows.

## Checks performed

- All upstream Python modules, README, dependency files and experiment notebook were inspected.
- Git working tree was clean and the independent `trust-rag` branch was created.
- Default-sandbox connections to PyPI, Hugging Face and GitHub failed with Windows socket permission error 10013.
- Permitted network checks succeeded for PyPI, Hugging Face and GitHub.
- BGE model download and a real query embedding succeeded: 768 dimensions.
- FlashRank model download and a real rerank succeeded (`relevance_score` returned).
- Original FlashRank compressor defaults to `top_n=3`, after dense `k=5`; this is kept in the reproduction.
- Real Edge browser upload, PDF parsing, chunking, Qdrant construction, dense retrieval, FlashRank reranking, generation, streaming and source display succeeded.
- Gemma 2 9B resolved digest: `ff02c3702f322b9e075e9568332d96c0a7028002f1a5a056e0a6784320a4db0b`.
- A first UI-test attempt matched Streamlit's loading-status expander too early and was discarded. The script now waits for the current answer's `Source #1` label. The service was restarted to clear interrupted history, and all three questions were rerun successfully.

## Actual smoke-test answers

| Type | Question | Actual answer | UI latency |
| --- | --- | --- | --- |
| Explicit | How many working days of paid sick leave do employees receive per year? | Employees receive 10 working days of paid sick leave per calendar year. | 4.839 s |
| Semantic | If I catch the flu and cannot work, how many paid days can I take off? | You can take up to 10 working days of paid sick leave. | 6.648 s |
| Unanswerable | What is the company's 2028 IPO valuation target? | This document does not include company valuation, IPO plans, or future stock prices. | 4.299 s |

These are three smoke-test measurements, not a reliability benchmark or latency distribution.
The original app's fixed session ID, shared storage, lost page metadata, source-expanders
and prompt-only refusal remain present in this reproduction.

The reproducible wrapper now reads an exact `git archive` snapshot of the original
commit. Run `python scripts/export_upstream.py` to restore that snapshot locally;
subsequent TrustRAG source changes therefore do not silently change the baseline.

## Phase 0 acceptance

- [x] Install original runtime dependencies with the documented Windows wheel compatibility patch.
- [x] Start a real local model, or an explicitly configured real remote model.
- [x] Upload and parse at least one PDF through the original app.
- [x] Confirm Qdrant retrieval and FlashRank reranking.
- [x] Ask an explicit-answer question.
- [x] Ask a semantic/paraphrase question.
- [x] Ask a question with no answer in the PDF.
- [x] Save actual answers and UI results.

Phase 0 is complete. No TrustRAG algorithm or benchmark-metric claims are implied by the smoke test.
