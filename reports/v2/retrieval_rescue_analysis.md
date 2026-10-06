# V2 Candidate rescue 分析

候选深度 K=10，hit 指至少一个 gold chunk 进入候选池。只统计可回答题。BM25 rescue 指 Dense Miss / BM25 Hit；Dense rescue 为反向条件。

| split | category | N | BM25 rescue | Dense rescue | Both Hit | Both Miss | Hybrid vs Dense | Hybrid-only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | all | 60 | 0 | 0 | 60 | 0 | 0 | 0 |
| dev | cross_document | 10 | 0 | 0 | 10 | 0 | 0 | 0 |
| dev | exact_term | 10 | 0 | 0 | 10 | 0 | 0 | 0 |
| dev | hard_negative | 10 | 0 | 0 | 10 | 0 | 0 | 0 |
| dev | numeric_date | 10 | 0 | 0 | 10 | 0 | 0 | 0 |
| dev | semantic | 10 | 0 | 0 | 10 | 0 | 0 | 0 |
| dev | version_conflict | 10 | 0 | 0 | 10 | 0 | 0 | 0 |
| test | all | 120 | 0 | 2 | 118 | 0 | 0 | 0 |
| test | cross_document | 20 | 0 | 0 | 20 | 0 | 0 | 0 |
| test | exact_term | 20 | 0 | 0 | 20 | 0 | 0 | 0 |
| test | hard_negative | 20 | 0 | 0 | 20 | 0 | 0 | 0 |
| test | numeric_date | 20 | 0 | 0 | 20 | 0 | 0 | 0 |
| test | semantic | 20 | 0 | 1 | 19 | 0 | 0 | 0 |
| test | version_conflict | 20 | 0 | 1 | 19 | 0 | 0 | 0 |

Hybrid-only 指两个分支都未命中而 Hybrid 命中；RRF 只重排分支并集，因此在相同 chunk gold 下这个计数必为零。它与 Hybrid 相对 Dense 的 rescue 不是同一概念。

原始 Dense/BM25 并集最多 20 个候选的覆盖率另存 `retrieval_rescue_summary.csv`，仅用于诊断；正式 Hybrid 仍由 RRF 截断为 10，不得把并集覆盖率称为正式 Hybrid Recall@20。逐题记录见 `retrieval_rescue_analysis.csv`。
