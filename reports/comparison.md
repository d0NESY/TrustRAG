# Formal test comparison

All rows use the frozen 120-question test split (90 answerable, 30 unanswerable), the same corpus/chunking/BGE embedding, ranking depth 10 and generation context depth 5. Each mode uses its own dev-calibrated evidence gate. No test values selected parameters. Original upstream whole-document results are reported separately in docs/original_baseline_results.md.

## Retrieval

| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@5 | Mean ms | P50 ms | P95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dense | 0.9333 | 0.9889 | 1.0000 | 1.0000 | 0.9615 | 0.9712 | 50.7114 | 50.1461 | 55.7292 |
| dense_reranker | 0.9667 | 1.0000 | 1.0000 | 1.0000 | 0.9833 | 0.9877 | 238.2588 | 238.1146 | 259.8203 |
| bm25 | 0.8111 | 0.9000 | 0.9667 | 0.9889 | 0.8693 | 0.8906 | 0.1245 | 0.1008 | 0.2070 |
| hybrid | 0.8889 | 1.0000 | 1.0000 | 1.0000 | 0.9407 | 0.9561 | 51.3655 | 50.5918 | 57.0670 |
| hybrid_reranker | 0.9778 | 1.0000 | 1.0000 | 1.0000 | 0.9889 | 0.9918 | 238.2876 | 236.2815 | 259.5609 |

## Generation

Correctness and groundedness use a fixed local Gemma 2 9B judge; every raw label is saved and is fallible. Citation accuracy below is deterministic gold-source precision, with semantic support judged separately. Answerability/FAR/FRR use gold booleans and actual published refusals. Different raw score scales are calibrated separately on dev.

| Method | Answer correctness (judge) | Groundedness (judge) | Citation accuracy (gold source) | Citation support (judge) | Answerability F1 | False answer rate | False refusal rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dense | 0.9111 | 1.0000 | 1.0000 | 1.0000 | 0.9535 | 0.0000 | 0.0889 |
| dense_reranker | 0.9333 | 1.0000 | 1.0000 | 1.0000 | 0.9655 | 0.0000 | 0.0667 |
| bm25 | 0.7556 | 1.0000 | 1.0000 | 1.0000 | 0.8608 | 0.0000 | 0.2444 |
| hybrid | 0.9000 | 1.0000 | 1.0000 | 1.0000 | 0.9474 | 0.0000 | 0.1000 |
| hybrid_reranker | 0.9333 | 1.0000 | 1.0000 | 1.0000 | 0.9655 | 0.0000 | 0.0667 |

## Gate ablation

Same Hybrid + Reranker test retrieval predictions, sources, generator and judge; only the evidence gate is disabled. This condition was declared before the test run.

| Gate | Answer correctness | Answerability F1 | False answer rate | False refusal rate |
| --- | --- | --- | --- | --- |
| enabled | 0.9333 | 0.9655 | 0.0000 | 0.0667 |
| disabled | 0.9888 | 0.9944 | 0.0000 | 0.0111 |

## Performance and cost

Warm query times are measured. Offline judge time is excluded from online total latency and reported separately. Local hardware/model hashes are in docs/model_artifacts.json. Local compute/electricity cost is not estimated.

| Method | Retrieval mean ms | Reranking mean ms | Generation mean ms | Total P50 ms | Total P95 ms | Judge mean ms | Input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dense | 50.6832 | 0.0000 | 1657.0443 | 1961.7948 | 2312.2614 | 1954.6793 | 120279 | 1976 |
| dense_reranker | 72.5051 | 165.7508 | 1608.4499 | 2126.1503 | 2432.9554 | 1890.1692 | 119292 | 1959 |
| bm25 | 0.0979 | 0.0000 | 1410.9991 | 1873.5564 | 2206.0530 | 1518.4287 | 101035 | 1726 |
| hybrid | 51.3387 | 0.0000 | 1682.8897 | 1979.4728 | 2269.9569 | 1842.0443 | 122693 | 2028 |
| hybrid_reranker | 71.9975 | 166.2876 | 1641.2729 | 2149.9032 | 2474.0918 | 1891.2459 | 120376 | 1975 |
