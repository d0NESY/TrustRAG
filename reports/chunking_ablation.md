# Chunking ablation (dev only)

All other settings are fixed: BGE embedding, dense retrieval, candidate depth 20, saved ranking depth 10, chunk size 2048 and overlap 128. Gold evidence is realigned by exact normalized source span. Models are warm. No test metrics are used for this choice.

| Strategy | Chunks | Recall@5 | MRR | nDCG@5 |
| --- | --- | --- | --- | --- |
| fixed | 120 | 1.0000 | 1.0000 | 1.0000 |
| recursive | 120 | 1.0000 | 1.0000 | 1.0000 |
| semantic_recursive | 146 | 1.0000 | 1.0000 | 1.0000 |

Selected: `recursive` by the predeclared dev objective.
