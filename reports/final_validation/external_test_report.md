# External Natural Document Test：检索完成，端到端 BLOCKED

公开 SQuAD2 官方 development data；第一优先级使用已有人工 QA/gold，未由 Gemma2 或 Codex 生成 QA。按原顺序选取首 15 个符合计数条件的不同文章家族，每个家族首段自然原文及首 3 positive / 2 impossible QA，共 75 题。PDF 为真实原文的忠实格式转换，不是模拟政策文档。

最终 Dense+Reranker、Gate OFF、Citation ON 配置未改变；实际检索使用原 BGE、原 FlashRank、原 chunk2048/128、candidate/final10、context top5。所有 75 题保留，45 个正例参与排序指标。

| dataset / same architecture | positive N | R@1 | R@5 | MRR | nDCG@5 |
| --- | --- | --- | --- | --- | --- |
| Synthetic V2 / Dense+CE | 120 | 0.958333 | 1.000000 | 0.979167 | 0.984622 |
| External native SQuAD2 / Dense+CE | 45 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

| metric | External - Synthetic point gap |
| --- | --- |
| recall@1 | 0.041667 |
| recall@5 | 0.000000 |
| mrr | 0.020833 |
| ndcg@5 | 0.015378 |

这是 descriptive cross-dataset generalization gap，数据、问题风格、规模和难度均不同，不能归因为模型退化或证明总体泛化。只有 15 个摘录，不是完整企业/高校政策语料；公开数据可能在预训练中出现。原 impossible label 是单段 context 范围，多文档全局有效性仍待独立审核。外测检索已经饱和，较小且主题分散的 corpus 不足以证明大规模困难自然检索优势；本轮外测未跑 Dense-only，不能将1.0000全部归因于重排器。

端到端生成/judge 因已记录 CUDA 运行环境故障 BLOCKED；全部所需生成指标 N/A，不与 V2 G0 生成数字相减或伪造“自然外测准确率”。Corpus、原生 aliases、source SHA、模型配置、完整 retrieval predictions 和两次执行错误均可查。
