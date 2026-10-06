# V2 Reranker 贡献

正 delta=重排前 gold 首次排名减去重排后排名。未进入前 10 的 gold 记为删失值 K+1=11；这不是观测到的第 11 名。同一比较严格验证候选池一致。

| split | comparison | category | N | mean delta | median delta | % improved | % degraded |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dev | dense -> dense_reranker | all | 60 | 0.5167 | 0.0000 | 25.0000 | 0.0000 |
| dev | hybrid -> hybrid_reranker | all | 60 | 0.1000 | 0.0000 | 11.6667 | 1.6667 |
| dev | dense -> dense_reranker | cross_document | 10 | 0 | 0.0000 | 0.0000 | 0.0000 |
| dev | hybrid -> hybrid_reranker | cross_document | 10 | 0 | 0.0000 | 0.0000 | 0.0000 |
| dev | dense -> dense_reranker | exact_term | 10 | 1.8000 | 1.0000 | 70.0000 | 0.0000 |
| dev | hybrid -> hybrid_reranker | exact_term | 10 | 0.2000 | 0.0000 | 20.0000 | 0.0000 |
| dev | dense -> dense_reranker | hard_negative | 10 | 0.3000 | 0.0000 | 10.0000 | 0.0000 |
| dev | hybrid -> hybrid_reranker | hard_negative | 10 | 0 | 0.0000 | 0.0000 | 0.0000 |
| dev | dense -> dense_reranker | numeric_date | 10 | 0 | 0.0000 | 0.0000 | 0.0000 |
| dev | hybrid -> hybrid_reranker | numeric_date | 10 | -0.1000 | 0.0000 | 0.0000 | 10.0000 |
| dev | dense -> dense_reranker | semantic | 10 | 0.1000 | 0.0000 | 10.0000 | 0.0000 |
| dev | hybrid -> hybrid_reranker | semantic | 10 | 0 | 0.0000 | 0.0000 | 0.0000 |
| dev | dense -> dense_reranker | version_conflict | 10 | 0.9000 | 1.0000 | 60.0000 | 0.0000 |
| dev | hybrid -> hybrid_reranker | version_conflict | 10 | 0.5000 | 0.5000 | 50.0000 | 0.0000 |
| test | dense -> dense_reranker | all | 120 | 0.6000 | 0.0000 | 30.0000 | 0.0000 |
| test | hybrid -> hybrid_reranker | all | 120 | 0.2500 | 0.0000 | 17.5000 | 0.8333 |
| test | dense -> dense_reranker | cross_document | 20 | 0.4000 | 0.0000 | 15.0000 | 0.0000 |
| test | hybrid -> hybrid_reranker | cross_document | 20 | -0.0500 | 0.0000 | 0.0000 | 5.0000 |
| test | dense -> dense_reranker | exact_term | 20 | 0.9500 | 0.0000 | 30.0000 | 0.0000 |
| test | hybrid -> hybrid_reranker | exact_term | 20 | 0.2000 | 0.0000 | 15.0000 | 0.0000 |
| test | dense -> dense_reranker | hard_negative | 20 | 0.1500 | 0.0000 | 15.0000 | 0.0000 |
| test | hybrid -> hybrid_reranker | hard_negative | 20 | 0 | 0.0000 | 0.0000 | 0.0000 |
| test | dense -> dense_reranker | numeric_date | 20 | 0 | 0.0000 | 0.0000 | 0.0000 |
| test | hybrid -> hybrid_reranker | numeric_date | 20 | 0 | 0.0000 | 0.0000 | 0.0000 |
| test | dense -> dense_reranker | semantic | 20 | 0.8500 | 0.0000 | 30.0000 | 0.0000 |
| test | hybrid -> hybrid_reranker | semantic | 20 | 0.2000 | 0.0000 | 10.0000 | 0.0000 |
| test | dense -> dense_reranker | version_conflict | 20 | 1.2500 | 1.0000 | 90.0000 | 0.0000 |
| test | hybrid -> hybrid_reranker | version_conflict | 20 | 1.1500 | 1.0000 | 80.0000 | 0.0000 |

逐题记录见 `reranker_rank_changes.csv`；候选缺失不能由当前重排器补回。排名统计反映首个相关 chunk，不等同于生成正确性。
