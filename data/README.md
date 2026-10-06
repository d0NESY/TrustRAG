# Northstar Labs demonstration knowledge base

This is an openly fictional, English-language enterprise knowledge base. No real
company policies, personal records, secrets, or private source documents are used.
The policy facts and gold questions/answers are authored together in
`scripts/build_demo_benchmark.py`. The PDF prose is templated and was not taken
from an external company. Gold answers are not produced by an LLM.

## Contents and split

- 10 PDF documents, each containing 12 independently identifiable policy sections.
- 120 answerable questions, each linked to a specific document and 1-based PDF page.
- 40 unanswerable questions, including missing details, future facts, private records,
  and unsupported entities; mere synonym or supported-format inference questions
  are not deliberately labeled unanswerable.
- Dev: 30 answerable + 10 unanswerable questions.
- Test: 90 answerable + 30 unanswerable questions.
- Seed: 42; stratified by document. Dev/test ask about different policy facts.
- `benchmark/manifest.json` records file hashes and dataset version `northstar-v1`.
- `source/facts.jsonl` contains the explicit source facts for independent audit.

The corpus is shared between dev and test, as in ordinary knowledge-base retrieval.
Questions and supervised fact targets do not overlap. This is **not** a held-out
document generalization benchmark. Parameter selection must use dev only.

## Rebuild

```powershell
.venv\Scripts\python.exe scripts/build_demo_benchmark.py
```

ReportLab's invariant mode fixes PDF metadata so a rebuild with the documented
dependency versions produces stable artifacts. Preserve the checked-in benchmark;
do not regenerate or change gold answers after inspecting formal test results.
Chunk alignment should be stored separately from raw dev/test files and must fail
explicitly when source evidence cannot be aligned.

## Limitations

This first version meets the requested minimum benchmark size. It is smaller than
the recommended final 200-300 answerable/50-100 unanswerable questions. The
templated prose, predominantly single-fact answers and synthetic policies can make
retrieval easier than a real enterprise corpus. Report its metrics as demonstration
results, not general reliability guarantees. Independent human audit and a public
or anonymized natural-document benchmark are appropriate later extensions.

`baseline/fictional_handbook.pdf` is a separate three-page upstream smoke-test
fixture and is not included in the controlled comparison corpus.
