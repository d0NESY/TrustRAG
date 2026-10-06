# V1 frozen baseline

V1 delivery commit: `b9253176a10342cb087054d0bc020eabf2b4e9b0`. Formal algorithm commit: `eeea01f`. All existing V1 artifacts/configs and inference code are protected by exact byte SHA-256. This file records the existing results without rerunning, relabeling or reinterpreting V1 test.

| V1 method | Recall@1 | Recall@5 | MRR | Mean retrieval + reranking ms |
| --- | --- | --- | --- | --- |
| dense | 0.9333 | 1.0000 | 0.9615 | 50.7 |
| bm25 | 0.8111 | 0.9667 | 0.8693 | 0.1 |
| dense_reranker | 0.9667 | 1.0000 | 0.9833 | 238.3 |
| hybrid | 0.8889 | 1.0000 | 0.9407 | 51.4 |
| hybrid_reranker | 0.9778 | 1.0000 | 0.9889 | 238.3 |

| V1 gate | End-to-end F1 | FAR | FRR |
| --- | --- | --- | --- |
| ON | 0.9655 | 0.0000 | 0.0667 |
| OFF | 0.9944 | 0.0000 | 0.0111 |

V2 uses separate data/benchmark_v2, experiments/v2 and reports/v2. No V1 test tuning is permitted.

Independent human review status: PENDING_HUMAN_REVIEW. Codex's earlier semantic inspection is not independent human review.
