# V2 架构决策

**Chosen architecture：Dense + Reranker + 原 grounding prompt + 引用核验。Current Gate 默认关闭，仅保留 experimental / optional。**

Dense + Reranker 的 test Recall@1 与 MRR 均更好，Hybrid 没有提供候选补回；额外词法索引与 RRF 的复杂度没有获得本轮质量收益支持。

## Measured benefit

Test 120 道 answerable：所选检索 R@1=0.9583、R@5=1.0000、MRR=0.9792、nDCG@5=0.9846、candidate R@10=1.0000。

Dense→Dense+Reranker 的 MRR delta=+0.1739，Hybrid→Hybrid+Reranker delta=+0.0835。Hybrid+Reranker 相对 Dense+Reranker R@1 delta=-0.0167、MRR delta=-0.0083。Test BM25 candidate rescue=0，实际 Hybrid rescue=0。

## Latency cost

所选检索 mean=2286.7 ms、P50=2242.9 ms、P95=2714.8 ms。Dense+Reranker mean=2286.7 ms，Hybrid+Reranker mean=2206.0 ms。Dense 重排相对不重排 mean 增加 2081.2 ms。

这是一次 warm-run 实测，包含所有 test queries；没有重复测量置信区间，不能把小差异当成确定性能优势。BM25/RRF 的工程成本还包括索引和融合参数维护。

## Rejected / non-default alternatives

- Dense：省去重排计算，但本集早期排序指标见正式对照；是否能接受质量损失取决于应用 SLA，当前优先保留重排。
- BM25：Test R@1=0.8083、MRR=0.8846、mean=0.573 ms；计算成本很低，但排序质量和候选覆盖低于所选方案。可作为延迟优先的独立对照，本次以检索质量为优先选择重排。
- Hybrid without reranker：RRF 同时涉及候选扩展和早期排序，不能仅按候选多样性选型。
- Hybrid + Reranker：本轮增益不足以支持把 BM25 + RRF 作为默认必选组件；保留实验对照配置。
- Current Gate：Test FAR 0.0250→0.0250，FRR 0.0083→0.0333，coverage 0.7500→0.7312；默认关闭，不把 relevance threshold 宣传为已证明的置信度防护。

## Failure modes and practical limits

候选缺失无法通过 reranker 修复；版本冲突、相邻标识符、cohort/数值混淆仍需逐题检查。RRF 前 10 丢失并集 gold=0；重排降级比例 Dense=0.00%、Hybrid=0.83%。Current Gate 新增误拒答=3，阻止 false answer=0。

分数只代表相关性；近似相关不等于存在所需事实。prompt/citation 核验并非完备事实校验，LLM judge 有误差。V2 合成数据不等于真实部署分布；每类仅 20 道 test，独立人工审阅仍为 PENDING_HUMAN_REVIEW。

G0/G1 生成实验只覆盖 Hybrid+Reranker。选择 Dense+Reranker 时，不据此冒称其 V2 端到端正确率、FAR 和延迟已测；后续若要验证部署质量，需要另行预先冻结生成对照，不能重新调整本次 gold/test。

## Decision rationale

架构选择是对冻结实验的工程取舍，不是 test 调参。保留原模型、分块、candidate K=10、final K=10 和重排参数；不新增功能。默认 demo 的 gate-off 配置与 V1 实验配置分开，V1 原配置保持冻结。所有逐题失败保存在 experiments/v2 和对应诊断 CSV。
