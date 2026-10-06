# Paired Bootstrap：V2 test 排序差异

使用全部 120 道 answerable test 问题，固定 seed=20261006、10,000 次有放回抽样。同一次 replicate 所有方法共享问题 ID；直接重算两方法指标差值，不比较两组单独 CI。

| unit | comparison | metric | point | bootstrap mean | 95% low | 95% high | P(delta>0) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| paired_question | dense_reranker - dense | recall@1 | 0.275000 | 0.274167 | 0.200000 | 0.358333 | 1.000000 |
| paired_question | dense_reranker - dense | recall@5 | 0.033333 | 0.033048 | 0.008333 | 0.066667 | 0.980600 |
| paired_question | dense_reranker - dense | mrr | 0.173929 | 0.173450 | 0.124206 | 0.225102 | 1.000000 |
| paired_question | dense_reranker - dense | ndcg@5 | 0.142081 | 0.141625 | 0.099307 | 0.188230 | 1.000000 |
| paired_family_cluster | dense_reranker - dense | recall@1 | 0.275000 | 0.274930 | 0.216667 | 0.333333 | 1.000000 |
| paired_family_cluster | dense_reranker - dense | recall@5 | 0.033333 | 0.033400 | 0.008333 | 0.066667 | 0.988400 |
| paired_family_cluster | dense_reranker - dense | mrr | 0.173929 | 0.173839 | 0.136925 | 0.211409 | 1.000000 |
| paired_family_cluster | dense_reranker - dense | ndcg@5 | 0.142081 | 0.142036 | 0.109671 | 0.175731 | 1.000000 |
| paired_question | dense_reranker - hybrid_reranker | recall@1 | 0.016667 | 0.016732 | 0.000000 | 0.041667 | 0.866500 |
| paired_question | dense_reranker - hybrid_reranker | recall@5 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| paired_question | dense_reranker - hybrid_reranker | mrr | 0.008333 | 0.008366 | 0.000000 | 0.020833 | 0.866500 |
| paired_question | dense_reranker - hybrid_reranker | ndcg@5 | 0.006151 | 0.006175 | 0.000000 | 0.015378 | 0.866500 |
| paired_family_cluster | dense_reranker - hybrid_reranker | recall@1 | 0.016667 | 0.016525 | 0.000000 | 0.041667 | 0.873500 |
| paired_family_cluster | dense_reranker - hybrid_reranker | recall@5 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| paired_family_cluster | dense_reranker - hybrid_reranker | mrr | 0.008333 | 0.008263 | 0.000000 | 0.020833 | 0.873500 |
| paired_family_cluster | dense_reranker - hybrid_reranker | ndcg@5 | 0.006151 | 0.006099 | 0.000000 | 0.015378 | 0.873500 |

解释：interval suggests 当前样本下的差异范围；不构成严格证明。P(delta>0) 是 bootstrap replicate 中正差值的频率，不是传统 p-value 或总体优越性的后验概率。CI 包含 0（含边界为 0）时，不能写显著优于。Recall@5 两种重排方法均饱和，差值区间为零也不能证明所有未来问题完全相同。

问题级 bootstrap 是本任务主分析；另以 20 个家族整组重采样作敏感性分析，保留家族内六道问题相关性。两种区间仍只描述该合成集，不解决作者偏差、预训练泄漏或外部领域泛化。

抽样索引、每次差值和 source prediction SHA256 保存于 experiments/final_validation/bootstrap_replicates.npz 与 bootstrap_provenance.json。正式结果未修改。
