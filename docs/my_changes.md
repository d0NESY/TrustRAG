# My changes and attribution

Upstream: curiousily/ragbase at `5af7b79162329fa0b725b39d1aeeea7eb1e4428b`. Formal evaluation core was frozen at `eeea01f`. License and upstream author attribution remain intact.

## Existing upstream modules

- `LICENSE`
- `README.md`
- `app.py`
- `poetry.lock`
- `pyproject.toml`
- `ragbase/__init__.py`
- `ragbase/chain.py`
- `ragbase/config.py`
- `ragbase/ingestor.py`
- `ragbase/model.py`
- `ragbase/retriever.py`
- `ragbase/session_history.py`
- `ragbase/uploader.py`

## Added implementation modules

- `ragbase/evaluation/__init__.py`
- `ragbase/evaluation/artifacts.py`
- `ragbase/evaluation/benchmark.py`
- `ragbase/evaluation/failure_analysis.py`
- `ragbase/evaluation/generation_metrics.py`
- `ragbase/evaluation/judge.py`
- `ragbase/evaluation/retrieval_metrics.py`
- `ragbase/evaluation/runtime.py`
- `ragbase/generation/__init__.py`
- `ragbase/generation/answerability.py`
- `ragbase/generation/citation.py`
- `ragbase/generation/generator.py`
- `ragbase/generation/prompt.py`
- `ragbase/ingestion/__init__.py`
- `ragbase/ingestion/chunker.py`
- `ragbase/ingestion/indexer.py`
- `ragbase/ingestion/parser.py`
- `ragbase/retrieval/__init__.py`
- `ragbase/retrieval/bm25.py`
- `ragbase/retrieval/dense.py`
- `ragbase/retrieval/fusion.py`
- `ragbase/retrieval/hybrid.py`
- `ragbase/retrieval/reranker.py`
- `ragbase/schema.py`
- `scripts/baseline_app.py`
- `scripts/build_demo_benchmark.py`
- `scripts/build_reports.py`
- `scripts/calibrate_answerability.py`
- `scripts/check_baseline_ui.py`
- `scripts/create_baseline_fixture.py`
- `scripts/download_ollama.py`
- `scripts/evaluate_generation.py`
- `scripts/evaluate_retrieval.py`
- `scripts/evaluate_upstream.py`
- `scripts/export_upstream.py`
- `scripts/ingest.py`
- `scripts/prefetch_baseline_models.py`
- `scripts/prefetch_models.py`
- `scripts/pull_local_model.py`
- `scripts/recompute_metrics.py`
- `scripts/record_model_artifacts.py`
- `scripts/run_ablation.py`
- `scripts/run_benchmark.py`
- `scripts/run_dev_matrix.py`
- `scripts/smoke_generation.py`
- `tests/test_answerability.py`
- `tests/test_benchmark.py`
- `tests/test_bm25.py`
- `tests/test_chunking.py`
- `tests/test_citation.py`
- `tests/test_failure_analysis.py`
- `tests/test_generation.py`
- `tests/test_generation_metrics.py`
- `tests/test_hybrid.py`
- `tests/test_metrics.py`
- `tests/test_model.py`
- `tests/test_rrf.py`

## Refactored behavior

- `config.py`: retained legacy constants, added validated YAML-backed experiment dataclasses. New runs use resolved configurations.
- `model.py`: retained Ollama/Groq/FastEmbed/FlashRank roles; added explicit configuration, bounded output/context, project caches and a verified seed API contract.
- New page-aware ingestion preserves filenames/pages and stable IDs; legacy ingestor remains available in the upstream snapshot.
- BM25 and RRF are established algorithms implemented/integrated here, not claimed as new inventions.
- Existing FlashRank is reused with explicit candidate/output depths and controlled experiments; the model itself is upstream functionality.
- Citations, dev-calibrated gates, benchmark alignment, model checksums, saved predictions, fixed judge and failure taxonomy are added engineering/evaluation capabilities.
- `app.py` now uses the new shared index/retrieval/generation pipeline, isolates upload/index directories and message history per session, preserves citations on rerender, and displays file/page evidence, score and refusal state. Real Edge upload, cited answer, refusal and reset checks passed. UI delivery follows the frozen formal algorithm experiments.

## Contribution boundary

PDF ingestion, semantic/recursive splitting, embedding, Qdrant, FlashRank, Streamlit, local/remote LLM support and upstream chat history predate this work. Resume claims should name the derivative project and attribute these correctly.

## Git diff evidence

Generated with `git diff 5af7b79162329fa0b725b39d1aeeea7eb1e4428b..HEAD` before final documentation/UI delivery. The final report records the delivery commit; rerun the command there for the full inventory.

```text
A	.gitattributes
M	.gitignore
A	configs/baseline.yaml
A	configs/bm25.yaml
A	configs/dense_reranker.yaml
A	configs/hybrid.yaml
A	configs/hybrid_reranker.yaml
A	data/README.md
A	data/baseline/fictional_handbook.pdf
A	data/benchmark/dev.jsonl
A	data/benchmark/manifest.json
A	data/benchmark/test.jsonl
A	data/documents/customer_support_faq.pdf
A	data/documents/employee_handbook.pdf
A	data/documents/expense_policy.pdf
A	data/documents/it_security_policy.pdf
A	data/documents/leave_policy.pdf
A	data/documents/onboarding_guide.pdf
A	data/documents/pricing_policy.pdf
A	data/documents/procurement_policy.pdf
A	data/documents/product_manual.pdf
A	data/documents/remote_work_policy.pdf
A	data/source/facts.jsonl
A	docs/baseline_environment.json
A	docs/baseline_reproduction.md
A	docs/baseline_screenshots/question_1.png
A	docs/baseline_screenshots/question_2.png
A	docs/baseline_screenshots/question_3.png
A	docs/baseline_ui_results.json
A	docs/baseline_windows_requirements.txt
A	docs/model_artifacts.json
A	docs/original_baseline_results.md
A	docs/upstream_baseline.md
A	experiments/bm25/dev/benchmark_aligned.jsonl
A	experiments/bm25/dev/calibration.json
A	experiments/bm25/dev/chunks.jsonl
A	experiments/bm25/dev/config.json
A	experiments/bm25/dev/resolved_config.json
A	experiments/bm25/dev/retrieval_metrics.json
A	experiments/bm25/dev/retrieval_predictions.jsonl
A	experiments/bm25/dev/run.log
A	experiments/chunking/fixed/benchmark_aligned.jsonl
A	experiments/chunking/fixed/chunks.jsonl
A	experiments/chunking/fixed/config.json
A	experiments/chunking/fixed/resolved_config.json
A	experiments/chunking/fixed/retrieval_metrics.json
A	experiments/chunking/fixed/retrieval_predictions.jsonl
A	experiments/chunking/fixed/run.log
A	experiments/chunking/recursive/benchmark_aligned.jsonl
A	experiments/chunking/recursive/chunks.jsonl
A	experiments/chunking/recursive/config.json
A	experiments/chunking/recursive/resolved_config.json
A	experiments/chunking/recursive/retrieval_metrics.json
A	experiments/chunking/recursive/retrieval_predictions.jsonl
A	experiments/chunking/recursive/run.log
A	experiments/chunking/semantic_recursive/benchmark_aligned.jsonl
A	experiments/chunking/semantic_recursive/chunks.jsonl
A	experiments/chunking/semantic_recursive/config.json
A	experiments/chunking/semantic_recursive/resolved_config.json
A	experiments/chunking/semantic_recursive/retrieval_metrics.json
A	experiments/chunking/semantic_recursive/retrieval_predictions.jsonl
A	experiments/chunking/semantic_recursive/run.log
A	experiments/dense/dev/benchmark_aligned.jsonl
A	experiments/dense/dev/calibration.json
A	experiments/dense/dev/chunks.jsonl
A	experiments/dense/dev/config.json
A	experiments/dense/dev/resolved_config.json
A	experiments/dense/dev/retrieval_metrics.json
A	experiments/dense/dev/retrieval_predictions.jsonl
A	experiments/dense/dev/run.log
A	experiments/dense/upstream_dev_baseline/config.json
A	experiments/dense/upstream_dev_baseline/resolved_config.json
A	experiments/dense/upstream_dev_baseline/retrieval_metrics.json
A	experiments/dense/upstream_dev_baseline/retrieval_predictions.jsonl
A	experiments/dense/upstream_dev_baseline/run.log
A	experiments/dense_reranker/dev/benchmark_aligned.jsonl
A	experiments/dense_reranker/dev/calibration.json
A	experiments/dense_reranker/dev/chunks.jsonl
A	experiments/dense_reranker/dev/config.json
A	experiments/dense_reranker/dev/resolved_config.json
A	experiments/dense_reranker/dev/retrieval_metrics.json
A	experiments/dense_reranker/dev/retrieval_predictions.jsonl
A	experiments/dense_reranker/dev/run.log
A	experiments/dense_reranker/upstream_dev_baseline/config.json
A	experiments/dense_reranker/upstream_dev_baseline/resolved_config.json
A	experiments/dense_reranker/upstream_dev_baseline/retrieval_metrics.json
A	experiments/dense_reranker/upstream_dev_baseline/retrieval_predictions.jsonl
A	experiments/dense_reranker/upstream_dev_baseline/run.log
A	experiments/hybrid/dev/benchmark_aligned.jsonl
A	experiments/hybrid/dev/calibration.json
A	experiments/hybrid/dev/chunks.jsonl
A	experiments/hybrid/dev/config.json
A	experiments/hybrid/dev/resolved_config.json
A	experiments/hybrid/dev/retrieval_metrics.json
A	experiments/hybrid/dev/retrieval_predictions.jsonl
A	experiments/hybrid/dev/run.log
A	experiments/hybrid_reranker/dev/benchmark_aligned.jsonl
A	experiments/hybrid_reranker/dev/calibration.json
A	experiments/hybrid_reranker/dev/chunks.jsonl
A	experiments/hybrid_reranker/dev/config.json
A	experiments/hybrid_reranker/dev/resolved_config.json
A	experiments/hybrid_reranker/dev/retrieval_metrics.json
A	experiments/hybrid_reranker/dev/retrieval_predictions.jsonl
A	experiments/hybrid_reranker/dev/run.log
A	experiments/retrieval_tuning/candidates_10_rrf_60/benchmark_aligned.jsonl
A	experiments/retrieval_tuning/candidates_10_rrf_60/chunks.jsonl
A	experiments/retrieval_tuning/candidates_10_rrf_60/config.json
A	experiments/retrieval_tuning/candidates_10_rrf_60/resolved_config.json
A	experiments/retrieval_tuning/candidates_10_rrf_60/retrieval_metrics.json
A	experiments/retrieval_tuning/candidates_10_rrf_60/retrieval_predictions.jsonl
A	experiments/retrieval_tuning/candidates_10_rrf_60/run.log
A	experiments/retrieval_tuning/candidates_20_rrf_10/benchmark_aligned.jsonl
A	experiments/retrieval_tuning/candidates_20_rrf_10/chunks.jsonl
A	experiments/retrieval_tuning/candidates_20_rrf_10/config.json
A	experiments/retrieval_tuning/candidates_20_rrf_10/resolved_config.json
A	experiments/retrieval_tuning/candidates_20_rrf_10/retrieval_metrics.json
A	experiments/retrieval_tuning/candidates_20_rrf_10/retrieval_predictions.jsonl
A	experiments/retrieval_tuning/candidates_20_rrf_10/run.log
A	experiments/retrieval_tuning/candidates_20_rrf_100/benchmark_aligned.jsonl
A	experiments/retrieval_tuning/candidates_20_rrf_100/chunks.jsonl
A	experiments/retrieval_tuning/candidates_20_rrf_100/config.json
A	experiments/retrieval_tuning/candidates_20_rrf_100/resolved_config.json
A	experiments/retrieval_tuning/candidates_20_rrf_100/retrieval_metrics.json
A	experiments/retrieval_tuning/candidates_20_rrf_100/retrieval_predictions.jsonl
A	experiments/retrieval_tuning/candidates_20_rrf_100/run.log
A	experiments/retrieval_tuning/candidates_20_rrf_60/benchmark_aligned.jsonl
A	experiments/retrieval_tuning/candidates_20_rrf_60/chunks.jsonl
A	experiments/retrieval_tuning/candidates_20_rrf_60/config.json
A	experiments/retrieval_tuning/candidates_20_rrf_60/resolved_config.json
A	experiments/retrieval_tuning/candidates_20_rrf_60/retrieval_metrics.json
A	experiments/retrieval_tuning/candidates_20_rrf_60/retrieval_predictions.jsonl
A	experiments/retrieval_tuning/candidates_20_rrf_60/run.log
A	experiments/retrieval_tuning/candidates_40_rrf_60/benchmark_aligned.jsonl
A	experiments/retrieval_tuning/candidates_40_rrf_60/chunks.jsonl
A	experiments/retrieval_tuning/candidates_40_rrf_60/config.json
A	experiments/retrieval_tuning/candidates_40_rrf_60/resolved_config.json
A	experiments/retrieval_tuning/candidates_40_rrf_60/retrieval_metrics.json
A	experiments/retrieval_tuning/candidates_40_rrf_60/retrieval_predictions.jsonl
A	experiments/retrieval_tuning/candidates_40_rrf_60/run.log
A	experiments/smoke_generation/config.json
A	experiments/smoke_generation/dev_predictions.jsonl
M	poetry.lock
M	pyproject.toml
M	ragbase/config.py
A	ragbase/evaluation/__init__.py
A	ragbase/evaluation/artifacts.py
A	ragbase/evaluation/benchmark.py
A	ragbase/evaluation/failure_analysis.py
A	ragbase/evaluation/generation_metrics.py
A	ragbase/evaluation/judge.py
A	ragbase/evaluation/retrieval_metrics.py
A	ragbase/evaluation/runtime.py
A	ragbase/generation/__init__.py
A	ragbase/generation/answerability.py
A	ragbase/generation/citation.py
A	ragbase/generation/generator.py
A	ragbase/generation/prompt.py
A	ragbase/ingestion/__init__.py
A	ragbase/ingestion/chunker.py
A	ragbase/ingestion/indexer.py
A	ragbase/ingestion/parser.py
M	ragbase/model.py
A	ragbase/retrieval/__init__.py
A	ragbase/retrieval/bm25.py
A	ragbase/retrieval/dense.py
A	ragbase/retrieval/fusion.py
A	ragbase/retrieval/hybrid.py
A	ragbase/retrieval/reranker.py
A	ragbase/schema.py
A	reports/answerability_calibration.json
A	reports/answerability_calibration.md
A	reports/chunking_ablation.json
A	reports/chunking_ablation.md
A	reports/retrieval_tuning.json
A	reports/retrieval_tuning.md
A	scripts/baseline_app.py
A	scripts/build_demo_benchmark.py
A	scripts/build_reports.py
A	scripts/calibrate_answerability.py
A	scripts/check_baseline_ui.py
A	scripts/create_baseline_fixture.py
A	scripts/download_ollama.py
A	scripts/evaluate_generation.py
A	scripts/evaluate_retrieval.py
A	scripts/evaluate_upstream.py
A	scripts/export_upstream.py
A	scripts/ingest.py
A	scripts/prefetch_baseline_models.py
A	scripts/prefetch_models.py
A	scripts/pull_local_model.py
A	scripts/recompute_metrics.py
A	scripts/record_model_artifacts.py
A	scripts/run_ablation.py
A	scripts/run_benchmark.py
A	scripts/run_dev_matrix.py
A	scripts/smoke_generation.py
A	tests/test_answerability.py
A	tests/test_benchmark.py
A	tests/test_bm25.py
A	tests/test_chunking.py
A	tests/test_citation.py
A	tests/test_failure_analysis.py
A	tests/test_generation.py
A	tests/test_generation_metrics.py
A	tests/test_hybrid.py
A	tests/test_metrics.py
A	tests/test_model.py
A	tests/test_rrf.py
```
