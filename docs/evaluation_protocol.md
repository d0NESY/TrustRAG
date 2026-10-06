# Evaluation protocol

## Source and chronology

1. Inspect and record upstream `5af7b79162329fa0b725b39d1aeeea7eb1e4428b`.
2. Reproduce the unmodified upstream algorithm in its original Streamlit UI with local Gemma 2 9B, including an explicit, paraphrase and unsupported question.
3. Freeze the fictional corpus and disjoint dev/test question/fact targets.
4. Run original Dense k=5 and original FlashRank top_n=3 on dev using the archived source, before algorithm changes.
5. Implement shared identities, page-aware chunks, BM25, RRF, citations and a calibrated evidence gate.
6. Select chunking and candidate/RRF settings on dev only; then calibrate each method's gate on the same dev split.
7. Verify real cited generation and fixed judge behavior on six dev examples.
8. Freeze the formal matrix at code commit `eeea01f`. All core Python files and scripts have a canonical content digest in the formal freeze file. Formal test is one logical run, with checkpoints for interruption recovery under identical parameters.

## Fixed data and model controls

- Corpus: Northstar Labs v1, ten synthetic PDFs, 120 pages, each page carrying one authored fact.
- Raw benchmark: 120 answerable and 40 unanswerable questions, seed 42.
- Dev: 30 positive / 10 negative. Test: 90 positive / 30 negative.
- Common controlled index: Recursive, 2048 normalized page characters, overlap 128.
- Shared BGE model, query/document embedding adapter and Qdrant cosine search.
- Dense and sparse candidate depth 10, RRF k=60, saved ranking depth 10, generation context depth 5.
- Original baseline uses whole-document semantic/recursive splitting and the upstream output depths. Its metrics are separate; differences cannot be assigned solely to fusion.
- Generator: local Gemma 2 9B, temperature 0, seed 42 forwarded in actual API options, maximum 192 output tokens, context 4096.
- Judge: same recorded Gemma 2 9B model, temperature 0, seed 42, JSON format, maximum 128 output tokens, fixed prompt in `ragbase/generation/prompt.py`.
- Each provided source excerpt is at most 1024 characters, ending at a complete word. Exact supplied quotes/offsets are saved.
- Public model revision, artifact checksums, Ollama 0.35.1 and LLM digest are checked; model weights are not committed.

## Development decisions

Chunking objective: MRR, then nDCG@5, then Hit@5. Exact ties prefer Recursive, Fixed, Semantic + Recursive. All three reached dev MRR 1.0000; Recursive was selected.

Candidate/RRF grid: (20,60), (10,60), (40,60), (20,10), (20,100). Objective: MRR, nDCG@5, Hit@5; exact ties prefer default 20/60, then fewer candidates. Depth 10 and 40 reached identical ranking metrics; 10/60 was selected. This is a small grid, not exhaustive optimization.

Gate objective: maximize dev F1, then minimize false answer rate, then false refusal rate. Features: top1, mean of available top three scores, and top1 minus top2 (top2 defaults to zero for a single result). Feature ties prefer top1, top3 mean, margin. All distinct score boundaries are scanned, plus all-answer/all-refuse boundary candidates. The comparison is per method; incompatible raw score scales are not mixed.

The same small dev set supplies several development choices. This is a stated overfitting risk, not held-out calibration validation. No test result selected a configuration.

## Metrics and denominators

| Metric | Definition |
| --- | --- |
| Recall@K | Unique relevant retrieved chunk IDs / all aligned gold chunk IDs, averaged over answerable questions |
| Hit@K | At least one aligned gold chunk in first K, over answerable questions |
| MRR | Reciprocal of first relevant saved rank; zero if missing; saved-depth truncation explicit |
| nDCG@5 | Binary relevance DCG / ideal DCG for the aligned gold set |
| Answerability precision | TP / (TP + FP), where positive prediction means a published answer |
| Answerability recall | TP / answerable gold |
| FAR | Published answers to unanswerable questions / all unanswerable gold |
| FRR | Refusals to answerable questions / all answerable gold |
| Answer correctness | Fixed LLM judge on answerable gold; system refusals count zero; judge parse failures separately counted/excluded |
| Groundedness | Fixed LLM judge on published answers and their actual cited quotes |
| Citation Accuracy | Gold-source precision across unique source references in published answers; relevance proxy, not claim entailment |
| Citation support | Separate fixed-judge decision on claim/source support and policy scope |
| Token F1 | Article/citation-normalized overlap; secondary lexical metric, not semantic correctness |

Source-ID validation occurs online; semantic citation support is evaluated offline. Invalid or missing IDs cause standardized refusal, and raw model output is kept. Model refusal is normalized, including removal of any text following the canonical refusal phrase.

## Formal matrix

E0 Dense; E1 Dense + Reranker; E2 BM25; E3 Hybrid; E4 Hybrid + Reranker. Each uses its saved dev-calibrated gate. E4 gate-disabled generation is a predeclared additional condition with exactly the same test retrieval input, sources and generation/judge settings. Its model calls are real, not substituted sample values.

`formal_test_freeze.json`, `retrieval_test_run.json` and `generation_run.json` preserve configuration, checksums and state. Resumption cannot change parameters. Completed predictions are replayed for metric recomputation; individual prediction records are never manually corrected to improve test scores.

## Timing and costs

Models are warm for query retrieval timing. Dense embedding, search and fusion are counted in retrieval; cross-encoder time is separate. Saved per-query wall time covers online retrieval plus generation processing; offline judge latency is separate. Negative/abstained queries remain in latency summaries. Each distribution includes mean, P50 and P95.

Ingestion parsing/chunking/indexing timings are saved in the shared index manifest. Local output stores API-reported `prompt_eval_count`/`eval_count`; prompt caching can reduce evaluated input tokens. No paid API was used. Local electricity or hardware amortization is not assigned a fabricated dollar cost. Groq estimation requires explicit token prices.

## Integrity and interpretation

Source facts, corpus bytes, question splits, alignments, models and code are traceable. Benchmarks were authored before retrieval changes. The data is small, templated and single-fact; excellent scores do not establish reliability on natural corporate documents, multilingual queries, OCR, cross-page or multi-hop tasks. Judge labels are not absolute truth and need independent review. Failure categories distinguish retrieval coverage/order, insufficient context, unsupported claims, wrong scope, refusal and false answers.
