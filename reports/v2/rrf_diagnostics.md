# V2 RRF 覆盖与排序诊断

比较 Dense 与固定 RRF Hybrid；不调 RRF k=60。覆盖增加、覆盖损失和首个 gold 排名变化分别统计，避免把候选扩展与排序混为一个收益。

| split | category | mean rank delta | improved % | degraded % | Hybrid rescue | Hybrid loss | Union gold dropped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dev | all | 0.4333 | 21.6667 | 0.0000 | 0 | 0 | 0 |
| dev | cross_document | 0 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| dev | exact_term | 1.6000 | 60.0000 | 0.0000 | 0 | 0 | 0 |
| dev | hard_negative | 0.3000 | 10.0000 | 0.0000 | 0 | 0 | 0 |
| dev | numeric_date | 0.1000 | 10.0000 | 0.0000 | 0 | 0 | 0 |
| dev | semantic | 0.1000 | 10.0000 | 0.0000 | 0 | 0 | 0 |
| dev | version_conflict | 0.5000 | 40.0000 | 0.0000 | 0 | 0 | 0 |
| test | all | 0.3333 | 18.3333 | 3.3333 | 0 | 0 | 0 |
| test | cross_document | 0.4500 | 15.0000 | 0.0000 | 0 | 0 | 0 |
| test | exact_term | 0.7500 | 25.0000 | 5.0000 | 0 | 0 | 0 |
| test | hard_negative | 0.1500 | 15.0000 | 0.0000 | 0 | 0 | 0 |
| test | numeric_date | 0 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| test | semantic | 0.6500 | 30.0000 | 5.0000 | 0 | 0 | 0 |
| test | version_conflict | 0 | 25.0000 | 10.0000 | 0 | 0 | 0 |

逐题见 `rrf_rank_changes.csv`。Union gold dropped 指 gold 存在于两个分支最多 20 项的并集，但 RRF 的前 10 丢弃了全部 gold。
