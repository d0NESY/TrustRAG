# Evidence gate calibration (dev only)

Each retrieval mode is calibrated on its own score scale. Dense, BM25 and RRF raw scores are never compared across scales. The main Hybrid + Reranker uses cross-encoder evidence. Each feature scans all distinct observed boundaries, including an all-refuse boundary. F1 is the predeclared objective, with false-answer/refusal tie breakers. These are retrieval-gate predictions, not final generation outcomes or probabilities.

| Method | Feature | Threshold | Precision | Recall | F1 | False answer rate | False refusal rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dense | margin | 0.019337284 | 0.9375 | 1.0000 | 0.9677 | 0.2000 | 0.0000 |
| dense_reranker | top1 | 0.06037676 | 0.9355 | 0.9667 | 0.9508 | 0.2000 | 0.0333 |
| bm25 | top1 | 7.3425881 | 0.8710 | 0.9000 | 0.8852 | 0.4000 | 0.1000 |
| hybrid | top1 | 0.032266458 | 0.8286 | 0.9667 | 0.8923 | 0.6000 | 0.0333 |
| hybrid_reranker | top1 | 0.039842352 | 0.9355 | 0.9667 | 0.9508 | 0.2000 | 0.0333 |
