# Candidate and RRF tuning (dev only)

Fixed corpus, chosen chunking, embedding, cross-encoder and saved ranking depth. The small grid changes one factor around the 20/60 default. It is not an exhaustive hyperparameter search.

| Candidates | RRF k | Recall@5 | MRR | nDCG@5 | Mean ms |
| --- | --- | --- | --- | --- | --- |
| 20 | 60 | 1.0000 | 0.9833 | 0.9877 | 460.77 |
| 10 | 60 | 1.0000 | 1.0000 | 1.0000 | 242.52 |
| 40 | 60 | 1.0000 | 1.0000 | 1.0000 | 857.38 |
| 20 | 10 | 1.0000 | 0.9833 | 0.9877 | 460.09 |
| 20 | 100 | 1.0000 | 0.9833 | 0.9877 | 463.18 |

Selected: `candidates_10_rrf_60`. No test metrics were inspected.
