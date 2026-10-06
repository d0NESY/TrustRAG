# TrustRAG V2：Hard Benchmark 与组件价值诊断

本轮使用真实本地模型运行，保留全部题目、原始预测和 judge 输出。最终推荐检索架构为 **Dense + Reranker**；证据门限默认关闭。Dense + Reranker 的 test Recall@1 与 MRR 均更好，Hybrid 没有提供候选补回；额外词法索引与 RRF 的复杂度没有获得本轮质量收益支持。

V1 正式 test、预测、指标、报告、原实验配置和 21 个核心算法文件保持原字节 SHA-256。V2 分支为 `trust-rag-v2`，冻结实验代码提交记录在每组 `resolved_config.json`。V1 的既有结论与数字只在 `V1_FROZEN_BASELINE.md` 原样记录，本轮不重新跑 V1 test，也不覆盖 V1 报告。

## 1. 数据与受控条件

V2 为 **240 题：180 answerable + 60 near-miss unanswerable**，来自 30 个政策家族、90 份 PDF、180 页。dev 为 80 题（60/20），test 为 160 题（120/40）。按整个文档家族隔离，六种正例类别在 test 中各 20 题，near-miss 40 题。

本数据集由 Codex 在模型评测前编写政策情景、事实和问题，属于**合成诊断集**，不是自然企业日志或真实客户问答，也不是独立人工编写的 gold。没有调用被评测的 Gemma2 来产生或修改参考答案；dataset metadata 中的 `no LLM gold` 表述应限于这一点，不表示没有 Codex 参与数据编写。独立人工 gold 验证未完成。操作指南、历史版本和附件仍有共同管理性结构，因此零字符串重叠不能证明不存在一切语义模板关联。source span 检查只覆盖标注 gold，公共行政说明存在复用。

gold 以 chunk 为单位。部分 hard-negative 的多个 cohort 事实位于同页/同一 gold chunk；检索命中不代表模型已经正确区分页内事实，仍要看生成答案。其难度不能等同于将每个 cohort 独立分块的对抗检索集。细节见 `BENCHMARK_CARD.md`。

`benchmark_integrity.json` 记录 family、normalized question、数字/标识符抽象 template、gold span 和近重复检查；没有跨 split 的命中项。所有语料均进入同一无监督索引，问题和目标文档家族隔离；这是检索知识库共享，不是 dev/test 的监督标签共享。

冻结 V1：同一 page-normalized recursive chunks（2048 字符/128 overlap）、BGE base en v1.5、FlashRank MiniLM L12、RRF k=60、候选 K=10、最终 K=10、生成 context top5。每个分支最多 10，Hybrid RRF 输出前 10；原始并集最多 20 仅供覆盖诊断。模型校验和与原参数见 `experiments/v2/formal_v2_freeze.json`。

Gemma2:9b 的生成/固定 judge、temperature=0、seed=42、num_ctx=4096、输出上限与 V1 一致。当前门限仍为 top1 ≥ 0.039842352271080017，没有在 V2 dev/test 重新校准。所有结果均为一次完整运行，支持同指纹 checkpoint 续跑；不对失败题做筛除。

独立人工审阅状态：**PENDING_HUMAN_REVIEW**。`reports/human_review_template.csv` 的人工字段为空。自动化检查、LLM judge 与 Codex 检查均不算独立人工审阅。

## 2. 检索总指标

ranking 仅统计 answerable；latency 统计全部题目，包含真实 query embedding、搜索/融合/重排，模型热身后测量，不使用查询 embedding 缓存。MRR 在保存深度 10 截断，nDCG@5 采用 binary chunk relevance。

| split | method | R@1 | R@3 | R@5 | R@10 | MRR | nDCG@5 | Candidate R@10 | Mean ms | P50 ms | P95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | dense | 0.6833 | 0.9500 | 0.9833 | 1.0000 | 0.8072 | 0.8507 | 1.0000 | 203.8008 | 201.8991 | 229.9138 |
| dev | bm25 | 0.8167 | 1.0000 | 1.0000 | 1.0000 | 0.9028 | 0.9280 | 1.0000 | 0.6115 | 0.5635 | 0.9712 |
| dev | dense_reranker | 0.9000 | 1.0000 | 1.0000 | 1.0000 | 0.9472 | 0.9609 | 1.0000 | 2059.5276 | 1986.2223 | 2775.0560 |
| dev | hybrid | 0.8333 | 1.0000 | 1.0000 | 1.0000 | 0.9111 | 0.9341 | 1.0000 | 203.3927 | 199.1631 | 228.1036 |
| dev | hybrid_reranker | 0.9000 | 1.0000 | 1.0000 | 1.0000 | 0.9500 | 0.9631 | 1.0000 | 2294.9513 | 2256.5829 | 2689.4285 |
| test | dense | 0.6833 | 0.9417 | 0.9667 | 1.0000 | 0.8052 | 0.8425 | 1.0000 | 205.5333 | 202.7639 | 233.9823 |
| test | bm25 | 0.8083 | 0.9583 | 0.9833 | 0.9833 | 0.8846 | 0.9097 | 0.9833 | 0.5728 | 0.5034 | 1.0400 |
| test | dense_reranker | 0.9583 | 1.0000 | 1.0000 | 1.0000 | 0.9792 | 0.9846 | 1.0000 | 2286.7272 | 2242.8657 | 2714.8334 |
| test | hybrid | 0.8000 | 0.9750 | 0.9917 | 1.0000 | 0.8873 | 0.9132 | 1.0000 | 205.3858 | 202.8956 | 228.1907 |
| test | hybrid_reranker | 0.9417 | 1.0000 | 1.0000 | 1.0000 | 0.9708 | 0.9785 | 1.0000 | 2205.9926 | 2176.8822 | 2504.0206 |

## 3. Test query-type breakdown

每类 20 道 answerable，不把类别小样本差异解释成普适或显著性结论。dev 和 test 完整明细见 `retrieval_by_category.csv`。

| category | method | R@1 | R@5 | MRR | nDCG@5 | Candidate R@10 |
| --- | --- | --- | --- | --- | --- | --- |
| cross_document | dense | 0.8500 | 0.9500 | 0.8988 | 0.9065 | 1.0000 |
| exact_term | dense | 0.7000 | 0.9000 | 0.7863 | 0.8031 | 1.0000 |
| hard_negative | dense | 0.8500 | 1.0000 | 0.9250 | 0.9446 | 1.0000 |
| numeric_date | dense | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| semantic | dense | 0.7000 | 0.9500 | 0.7963 | 0.8290 | 1.0000 |
| version_conflict | dense | 0.0000 | 1.0000 | 0.4250 | 0.5720 | 1.0000 |
| cross_document | bm25 | 0.9500 | 1.0000 | 0.9667 | 0.9750 | 1.0000 |
| exact_term | bm25 | 0.7500 | 1.0000 | 0.8600 | 0.8955 | 1.0000 |
| hard_negative | bm25 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| numeric_date | bm25 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| semantic | bm25 | 0.9000 | 0.9500 | 0.9250 | 0.9315 | 0.9500 |
| version_conflict | bm25 | 0.2500 | 0.9500 | 0.5558 | 0.6563 | 0.9500 |
| cross_document | dense_reranker | 0.9500 | 1.0000 | 0.9750 | 0.9815 | 1.0000 |
| exact_term | dense_reranker | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| hard_negative | dense_reranker | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| numeric_date | dense_reranker | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| semantic | dense_reranker | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| version_conflict | dense_reranker | 0.8000 | 1.0000 | 0.9000 | 0.9262 | 1.0000 |
| cross_document | hybrid | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| exact_term | hybrid | 0.8500 | 1.0000 | 0.9167 | 0.9381 | 1.0000 |
| hard_negative | hybrid | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| numeric_date | hybrid | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| semantic | hybrid | 0.9000 | 1.0000 | 0.9375 | 0.9531 | 1.0000 |
| version_conflict | hybrid | 0.0500 | 0.9500 | 0.4696 | 0.5882 | 1.0000 |
| cross_document | hybrid_reranker | 0.9500 | 1.0000 | 0.9750 | 0.9815 | 1.0000 |
| exact_term | hybrid_reranker | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| hard_negative | hybrid_reranker | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| numeric_date | hybrid_reranker | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| semantic | hybrid_reranker | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| version_conflict | hybrid_reranker | 0.7000 | 1.0000 | 0.8500 | 0.8893 | 1.0000 |

按本集 MRR 的类别最佳（含并列）：

| category | best methods | MRR |
| --- | --- | --- |
| cross_document | hybrid | 1.0000 |
| exact_term | dense_reranker, hybrid_reranker | 1.0000 |
| hard_negative | bm25, dense_reranker, hybrid, hybrid_reranker | 1.0000 |
| numeric_date | dense, bm25, dense_reranker, hybrid, hybrid_reranker | 1.0000 |
| semantic | dense_reranker, hybrid_reranker | 1.0000 |
| version_conflict | dense_reranker | 0.9000 |

## 4. Q1：原版到 TrustRAG 的 dev 增益如何归因？

原版复现实验的 dev Dense Recall@1=0.7667、MRR=0.8472，原版 Dense+Reranker Recall@1=0.8000、MRR=0.8389；V1 修改后的 dev Dense 与 Dense+Reranker 均为 1.0000。上述已有记录来自 `docs/original_baseline_results.md` 与 `experiments/*/dev/retrieval_metrics.json`，没有重测。

这不是仅替换 retrieval algorithm 的对照：原版整文档语义分块与页面元数据丢失，后续变为保留页信息的分块/对齐；Dense depth 从 5 变为 10，原版 FlashRank 最多输出 3，后续输出 10；索引、chunk identity 与 gold 对齐方式也不同。因此只能把大幅变化归为 **pipeline / chunking / depth / metadata 的联合变化**，无法给各因素分配单独因果份额，更不能把 0.8→1.0 归给新 BM25/RRF 或重排器。FlashRank 本身也是上游已有组件。

可作算法归因的是共享 chunks、模型、候选与最终预算的受控五组比较：V2 的 Dense→Dense+Reranker、Hybrid→Hybrid+Reranker 是对候选池不变的排序贡献；Dense→Hybrid 同时改变候选构成与 RRF 排序，需分开报告覆盖和排名。

## 5. Q2：Reranker 是否仍然有效？

两种候选源上的总体 MRR 均提高，重排仍是本轮可直接归因的有效排序组件。

Test Dense→Dense+Reranker：R@1 0.6833→0.9583，MRR 0.8052→0.9792；首 gold 的 mean rank improvement=0.6000、median=0.0000，improved=30.00%、degraded=0.00%。

Test Hybrid→Hybrid+Reranker：R@1 0.8000→0.9417，MRR 0.8873→0.9708；mean=0.2500、median=0.0000，improved=17.50%、degraded=0.83%。

完整类别分布见 `reranker_contribution.md`，逐题变化见 `reranker_rank_changes.csv`。候选池一致性已自动核验。Cross-Encoder 能改变现有候选的相对位置，不能找回未进入候选的 gold；降级案例完整保留。这里的“稳定”只指当前受控数据与两种候选源，不代表跨随机种子、领域或生成模型的稳定性。

dense -> dense_reranker 的平均首 gold 排名改善最多的类别为 version_conflict（delta=1.25）、exact_term（delta=0.95）、semantic（delta=0.85）。 hybrid -> hybrid_reranker 的平均首 gold 排名改善最多的类别为 version_conflict（delta=1.15）、exact_term（delta=0.20）、semantic（delta=0.20）。 具体 improved/degraded 案例见 `diagnostic_examples.md`，按 question ID 固定排序取例，全部逐题记录仍保留。

## 6. Q3：BM25 在哪些类型存在 unique rescue？

Test K=10：BM25 rescue=0，Dense rescue=2，Both Hit=118，Both Miss=0；Hybrid 实际相对 Dense rescue=0。按类别的全部计数见 `retrieval_rescue_analysis.md`。

本轮 test 没有 BM25 candidate unique rescue，不能凭 exact-term 的类别设计就宣称词法分支具有独有覆盖收益。词法排序上的局部收益需看 breakdown，与候选补回是两种证据。


Hybrid-only hit（两个分支都 miss 而 Hybrid hit）=0。RRF 只处理分支并集，该条件在此定义下结构性不可能，不能用它否认 Hybrid 相对 Dense 的 rescue。

## 7. Q4：Hybrid 是否改善 candidate recall？

Test Dense candidate R@10=1.0000，Hybrid=1.0000，差值=+0.0000。原始 Dense/BM25 并集（最多 20，非正式 Hybrid 输出）的 recall=1.0000。

Hybrid rescue vs Dense=0、Hybrid loss vs Dense=0；并集中有 gold 但 RRF 前 10 丢弃全部 gold 的题目=0。仅当真实固定预算 Hybrid 的覆盖率上升，才能宣称 candidate recall 改善；并集的更大预算不能作为同预算收益。

## 8. Q5：RRF 是否损害 early ranking？

Test Dense→Hybrid：R@1 0.6833→0.8000，MRR 0.8052→0.8873，nDCG@5 0.8425→0.9132。首 gold rank improved=18.33%、degraded=3.33%，mean delta=0.3333。

本轮没有观察到 RRF 在总体 MRR 上的损失；仍需保留逐题降级与截断失败。


## 9. Q6：Hybrid+Reranker 的收益是否支持额外复杂度？

Test 对 Dense+Reranker：R@1 delta=-0.0167、R@5 delta=+0.0000、MRR delta=-0.0083。mean latency 2286.7→2206.0 ms，差值=-80.7 ms，P95 2714.8→2504.0 ms。

Dense + Reranker 的 test Recall@1 与 MRR 均更好，Hybrid 没有提供候选补回；额外词法索引与 RRF 的复杂度没有获得本轮质量收益支持。 复杂度包括 BM25 索引维护、额外候选配置和 RRF 融合，而不是仅以某次毫秒差衡量。实测时间是同机、按方法顺序的一次运行，未做随机交错重复和误差估计；小延迟差不能宣称统计显著。V1 与 V2 查询、chunk 数量/长度和运行时负载不同，不能把跨版本 latency 差单独归因于算法。

补充诊断发现：两种重排候选池共享的 passage 在固定 ONNX 权重下也有保存分数差异，test 平均绝对差=0.003428、最大=0.115434。Hybrid 重排比 Dense 重排降级的题目中，Hybrid top1 本来就在 Dense 候选池的题目=2，不能把这些失败直接解释为 BM25 引入了新坏候选。FlashRank 按整个候选 batch 进行动态 padding/量化 ONNX 推理，batch 构成引起数值变化是待验证的机制假设；本轮只记录原预测中的 score drift，没有额外重跑或修复模型。详见 `reranker_shared_score_changes.csv` 与 `reranker_between_pools_rank_changes.csv`。

## 10. G0/G1：实际发布回答与单独 Gate

G0 保留原 grounding prompt 和引用 ID 核验，关闭分数 gate；G1 只开启原 V1 门限。两者共用 Hybrid+Reranker 已保存的检索结果。正例=实际发布非拒答；Precision/Recall/F1 是“是否应回答”的分类指标，不是答案内容正确率。

| split | condition | Precision | Recall | F1 | FAR | FRR | Coverage | TP | FP | FN | TN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | G0_prompt_only | 1.0000 | 0.9667 | 0.9831 | 0.0000 | 0.0333 | 0.7250 | 58 | 0 | 2 | 20 |
| dev | G1_current_v1_gate | 1.0000 | 0.9667 | 0.9831 | 0.0000 | 0.0333 | 0.7250 | 58 | 0 | 2 | 20 |
| test | G0_prompt_only | 0.9917 | 0.9917 | 0.9917 | 0.0250 | 0.0083 | 0.7500 | 119 | 1 | 1 | 39 |
| test | G1_current_v1_gate | 0.9915 | 0.9667 | 0.9789 | 0.0250 | 0.0333 | 0.7312 | 116 | 1 | 4 | 39 |

单独 Gate 的允许/拒绝决策（尚未经过 LLM prompt 与引用检查）：

| split | Precision | Recall | F1 | FAR | FRR | Coverage | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | 0.8676 | 0.9833 | 0.9219 | 0.4500 | 0.0167 | 0.8500 | 9 | 1 |
| test | 0.8864 | 0.9750 | 0.9286 | 0.3750 | 0.0250 | 0.8250 | 15 | 3 |

生成质量（固定本地 LLM judge，非独立人工）：

| split | condition | Correctness | Correctness N | Groundedness | Gold-source citation precision | Judge failures | Total P50 ms | Total P95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | G0_prompt_only | 0.9667 | 60 | 1.0000 | 0.9153 | 0 | 4309.2770 | 5171.9301 |
| dev | G1_current_v1_gate | 0.9667 | 60 | 1.0000 | 0.8983 | 0 | 4306.5980 | 5212.4461 |
| test | G0_prompt_only | 0.9833 | 120 | 1.0000 | 0.9250 | 0 | 4312.0333 | 5004.5623 |
| test | G1_current_v1_gate | 0.9583 | 120 | 1.0000 | 0.9231 | 0 | 4232.2812 | 4824.7756 |

配对变化（G1 相对 G0）与门限直接影响分别列出：

| split | G0 false answer→G1 refusal | Direct gate prevented | Added false refusal | Direct gate added refusal | Changed raw answer after pass |
| --- | --- | --- | --- | --- | --- |
| dev | 0 | 0 | 1 | 1 | 1 |
| test | 0 | 0 | 3 | 3 | 0 |

judge 的无效 JSON 计入 failure count 并保留原输出，不填人工标签。Correctness 把 answerable 上拒答计为 0，其余 judge 失败按 V1 metric 定义排除并报告分母。gold-source citation precision 是来源相关性代理，不代表逐主张蕴含。online total 包含检索和生成，不包含离线 judge。

## 11. Q7：Current Gate 是否终于降低 False Answer？

Current Gate 没有降低困难 near-miss 的 False Answer Rate。 Test FAR 0.0250→0.0250，FRR 0.0083→0.0333，coverage 0.7500→0.7312。配对分析：G1 拒绝了 G0 的 false answer=0，G1 新增 false refusal=3。其中由分数门限直接阻止的 false answer=0，门限直接新增的 false refusal=3。逐题见 `gate_case_changes.csv`。

新增误拒答中，gold chunk 已在生成 context 内的题目=3，完整标注 evidence span 在来源摘录中可按规范化字符串找到的题目=3。后者只检查完整字符串存在，不能把未命中直接解释为没有可用事实，也不是独立人工正确性标签。分类误拒答率见 `gate_by_category.csv`。

门限放行后的两次 raw answer 不同的题目=0；相同 prompt 的对应关系也保存在逐题 CSV。即使固定 seed，也不能先验假设两次运行完全相同。门限直接拒绝与放行后生成差异必须区分，所有结果照实计入。

当前门限保持 experimental / optional，demo 默认关闭。本轮不基于 V2 test 调阈值。 如果 FAR 存在下降，也不能在没有明确可接受的 FRR/coverage 证据时自动恢复默认开启。无观察错误不等于真实风险为零；test near-miss 仅 40 题。

## 12. Q8：为什么 relevance score 不能直接当作 answerability confidence？

Test top1 AUC（高分视为 answerable）=0.9631，20 等宽 bin 的 class-normalized overlap coefficient=0.1583；当前门限单独 FAR=0.3750、FRR=0.0250。两个分布的全部 quantile、histogram、逐题 top1/top3_mean/margin 与标签分别保存在 `answerability_score_quantiles.csv`、`answerability_score_histograms.csv`、`answerability_scores.csv` 和 `answerability_score_distributions.json`。

本轮 top1 具有较强整体区分信号，不能把它描述为“两类分布高度重叠”或“完全没有 answerability 信息”。但高分 near-miss `v2_rail_booking_near_miss_2` 的 top1=0.977644，低分可回答题 `v2_device_exit_exact_term` 的 top1=0.016206，说明尾部仍有真实重叠，当前低门限并不能独立判断事实充足性。高 AUC、门限决策质量和端到端净收益是不同结论。

最高分 near-miss 的原问题：**Which client allows employees to claim first-class rail travel?**；G0 输出：**Executives travelling on client business may book first class. [S1]**。在本集这个例子中，回答给出员工群体的车票规则，而问题需要材料未提供的客户身份。有引用且陈述受到来源支持，仍然可以答非所问；不能用相关性高分或 groundedness 代替所问事实存在性。

| feature | answerable | N | P5 | P25 | P50 | P75 | P95 | AUC | Binned overlap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| top1 | True | 120 | 0.5407 | 0.9590 | 0.9938 | 0.9989 | 0.9997 | 0.9631 | 0.1583 |
| top1 | False | 40 | 0.0001 | 0.0003 | 0.0090 | 0.3360 | 0.9139 | 0.9631 | 0.1583 |
| top3_mean | True | 120 | 0.2102 | 0.3270 | 0.3424 | 0.5816 | 0.9828 | 0.9415 | 0.2000 |
| top3_mean | False | 40 | 0.0001 | 0.0002 | 0.0032 | 0.1139 | 0.3314 | 0.9415 | 0.2000 |
| margin | True | 120 | 0.0002 | 0.1553 | 0.8174 | 0.9640 | 0.9961 | 0.8275 | 0.3667 |
| margin | False | 40 | 0.0000 | 0.0001 | 0.0054 | 0.3318 | 0.8538 | 0.8275 | 0.3667 |

Cross-Encoder 学到的是 query/document relevance，不是“该材料是否包含问题指定事实”的概率。Near-miss 可以共享主题、对象与日期词，却缺失未来年份、具体金额或约定条件；因此可能产生高相关分但仍不可回答。反过来，语义改写、精确标识符或有效版本选择可能分数偏低，但 gold 事实确实存在。top3_mean 和 margin 也只是排序形态，AUC 与量化重叠是诊断，不是新置信度模型或重新校准结果。

若同一 feature 的正/负分布存在实际范围重叠，本集不支持把它作为单独 answerability confidence。即使某个特征的 AUC 较高，也不能把未经概率校准的 score 当作可靠概率，或在已经看过 test 后选择新特征/阈值。重排器解决相关性排序；prompt 与引用核验负责当前发布策略的部分防护，两者仍可能遗漏具体事实缺失或版本错误。

## 13. 最终架构与限制

完整选择、替代方案、收益、latency、失败模式见 `architecture_decision.md`。V2 只运行五组检索与 Hybrid+Reranker 上 G0/G1 的端到端门限对照；没有宣称所选 Dense+Reranker 在 V2 上已经完成新的生成质量实验。检索架构选择与已测 gate 结果必须分开看。

本轮没有增加 query rewrite、HyDE、multi-query、Agent、GraphRAG、训练或图结构。没有因结果不利而改 gold、删题或调 test。该诊断集在 early ranking、版本、hard negatives 和拒答上可暴露失败，但候选 R@10 或 R@5 若仍接近饱和，需明确承认剩余难度限制；未来更自然独立语料属于另一次事先冻结的研究，不修改本轮。

复现命令见 `REPRODUCE.md`。`artifact_verification.json` 记录所有 V2 实验文件 SHA-256、完整预测计数、逐组 metric 重新计算与 V1 hash 检查结果。额外字节快照保留 262 个 V1 文件（包括原保护清单、核心代码和既有文档）的精确原字节，供独立新 clone 处理 Git 的换行转换；原工作目录不允许恢复写入。新增 V2 文件通过 `.gitattributes` 保留字节。人工复核仍待完成。

真实浏览器 smoke 检查已完成：默认 Dense + 重排、门限关闭、带引用回答、prompt 拒答、实际 PDF 上传、文件名/页码展示和清空聊天记录。截图与原始 UI 文本保存在 `demo_screenshots/` 和 `demo_ui_results.json`；当前 V2 服务使用 http://127.0.0.1:8502。
