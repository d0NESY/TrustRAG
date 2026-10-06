# Original RagBase retrieval baseline (dev only)

Actual measurements using the frozen upstream source and whole-document chunking. The original dense depth is 5 and FlashRank returns at most 3; Recall@10 is therefore capped by the saved ranking depth. These results precede retrieval algorithm changes and are separate from the later controlled five-method comparison.

| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@5 | Mean ms | P50 ms | P95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dense | 0.7667 | 0.9333 | 0.9667 | 0.9667 | 0.8472 | 0.8774 | 84.2062 | 84.4687 | 98.6670 |
| dense_reranker | 0.8000 | 0.9000 | 0.9000 | 0.9000 | 0.8389 | 0.8544 | 273.8217 | 274.3237 | 306.5716 |
