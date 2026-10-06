# TrustRAG 最终可信度验证

本轮只验证冻结结论，没有新增 retrieval 算法、调 test 或改 V1/V2 结果。继续选择 **Dense + Existing Cross-Encoder Reranker；Gate 默认 OFF；原 Citation Logic 保留**。统计证据支持其在当前 V2 数据上相对 Dense 的排序收益；对 Hybrid+Reranker 的领先仍只是较高点估计，不宣称显著优于。

状态：Bootstrap / Reranker Stability / Batch Composition / Latency Repeatability **COMPLETE**；Human Audit **PENDING_HUMAN_REVIEW**；External retrieval **COMPLETE**，External generation/judge **BLOCKED**。封版包含全部可完成验证和明确的未完成项，不开启 V3。

## 1. 冻结输入保护

V2 完成交付提交为 `c0eaa39`。新分支 `trust-rag-final-validation` 的新实验与报告只写入 final_validation；原 app、算法、配置、predictions、metrics、benchmark 与报告未改变。`frozen_artifact_manifest.json` 保护 580 个既有文件；另核对 V1 清单、V1 精确字节快照及 V2 实验/日志 SHA。新简历文档仅写 docs/final_resume_claims.md。

既有模型与配置保持不变：BGE base en v1.5、ms-marco MiniLM L12、Gemma2:9b；原模型 checksum、candidate/final K=10、context top5、chunk2048/128、seed42 均未重调。验证 driver 是新观察脚本，不改推理模块。

## 2. Human Audit：状态清楚区分

已检查原 reports/review_samples.jsonl 与 reports/human_review_template.csv，旧模板没有人工填写结果。整理 28 条目的性样本，覆盖 LLM-judged correct/incorrect、正确拒答、False Answer、False Refusal、版本冲突、Hard Negative、near-miss 和引用边界。四个人工字段共 112 格，目前填入 0 格；全部保持空白，没有由 Codex 代填。

允许 1 / 0 / UNCERTAIN；审核说明、原始来源摘录与 cited_sources 已提供，judge 标签另存以减轻锚定偏差。人工准确率、groundedness、citation validity、gold agreement 与 Human/LLM agreement 当前均 N/A。目的性样本未来的审核准确率也不能代替全量 test 随机抽样准确率。见 human_audit_summary.md、HUMAN_AUDIT_PENDING.md 和 human_audit_template.csv。

## 3. Paired Bootstrap 95% CI

全部 120 道 answerable V2 test 问题，10,000 replicates，seed=20261006。每次有放回抽取相同 question IDs 给所有方法，直接计算差值。以下为主问题级分析：

| comparison | metric | point | bootstrap mean | 95% low | 95% high | P(delta>0) |
| --- | --- | --- | --- | --- | --- | --- |
| dense_reranker - dense | recall@1 | 0.275000 | 0.274167 | 0.200000 | 0.358333 | 1.000000 |
| dense_reranker - dense | recall@5 | 0.033333 | 0.033048 | 0.008333 | 0.066667 | 0.980600 |
| dense_reranker - dense | mrr | 0.173929 | 0.173450 | 0.124206 | 0.225102 | 1.000000 |
| dense_reranker - dense | ndcg@5 | 0.142081 | 0.141625 | 0.099307 | 0.188230 | 1.000000 |
| dense_reranker - hybrid_reranker | recall@1 | 0.016667 | 0.016732 | 0.000000 | 0.041667 | 0.866500 |
| dense_reranker - hybrid_reranker | recall@5 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| dense_reranker - hybrid_reranker | mrr | 0.008333 | 0.008366 | 0.000000 | 0.020833 | 0.866500 |
| dense_reranker - hybrid_reranker | ndcg@5 | 0.006151 | 0.006175 | 0.000000 | 0.015378 | 0.866500 |

Dense+CE − Dense：R@1 delta=+0.275、MRR delta≈+0.1739；bootstrap interval suggests 明确的当前样本排序收益。Dense+CE − Hybrid+CE：R@1 delta≈+0.0167、MRR delta≈+0.0083，但两个区间都包含 0，不能写统计学证明或显著优于。差别只来源于两道版本题，其余 118 道首次 gold rank 相同。

另做 20 家族 paired cluster bootstrap 作为敏感性分析，两种分析都保留在 bootstrap_report.md；不假设六道家族内问题完全独立。P(delta>0) 是 resampling 正差值频率，不是传统 p-value 或总体优越性的后验概率。当前 CI 仍不能解决合成作者偏差、小类别 N=20 或外部自然语料差异。


## 4. Reranker Stability 与 Batch Effect

固定 30 个诊断问题：10 version-conflict、10 exact-term、10 semantic，优先较大旧 shared-score drift，并包含两道已知版本翻转。两个方法各 5 次，合计 300 次真实 timed query；每次候选列表及其顺序都与原正式保存列表核对。score std 最大值=0.000000、max-min 最大值=0.000000，排名变化 passage 数=0。所有问题的 pairwise Top1 / 完整排名 agreement 均为 1；与正式排序一致。3000 个 score 对比正式值的最大差=0.000000。

这支持固定输入条件下的重复稳定，不能推断所有候选 batch 都等价。另对 6 道诊断题做 A/B/C/single-pair 各三次：固定 query、target 与 competitor 内容，固定 target/competitor 在 slot0/slot1，仅替换其他八个 passage。A/B/C size=10，single=1 仅为离线诊断，不变更生产候选预算。完整输入 token length、padding、score、rank、top1/top5/top10 都保存。

共有 2 道 case 出现固定 target/competitor margin 变号，并改变目标的 Top1 状态。parental_requests 的目标 score 从 A=0.918854 到 B=0.927871，但 competitor 变化更大，margin +0.019064→−0.011525；research_data 的 margin +0.000153→−0.000114，也使目标 rank1→rank2。其余四例有分数变化，实际 target 排序未变；六例 target 都仍在 Top5。single-pair rank1 是结构性结果，不代表排序改善。

因此 batch composition 影响当前实现输出有直接实验支持；动态 padding / ONNX quantization 的具体因果贡献仍为 **mechanism hypothesis**。没有通过改换模型/量化版本/参数做根因归因，不能写“已证明由量化引起”。见 reranker_stability.csv、reranker_rank_agreement.csv、reranker_batch_scores.csv 和 reranker_batch_effect.md。

## 5. Latency Repeatability

同一真实 300-query 五轮过程同时承担稳定性和延迟验证，没有再造计时结果。每个方法每轮先做两次 full retrieve warmup；query embedding 实际重算，模型/index 缓存热身，不缓存查询向量。每轮方法顺序由固定种子随机抽取，顺序清单见 protocol.json。

| method | round metric | mean across 5 ms | std ms | min ms | max ms |
| --- | --- | --- | --- | --- | --- |
| dense_reranker | mean_ms | 1772.994259 | 31.164985 | 1721.309777 | 1800.274443 |
| dense_reranker | p50_ms | 1751.593570 | 22.343458 | 1719.985850 | 1782.736900 |
| dense_reranker | p95_ms | 2007.259309 | 126.502696 | 1820.742640 | 2121.894515 |
| hybrid_reranker | mean_ms | 1692.990927 | 273.566400 | 1214.033260 | 1891.068700 |
| hybrid_reranker | p50_ms | 1735.185450 | 42.674000 | 1666.885650 | 1767.388650 |
| hybrid_reranker | p95_ms | 2172.471325 | 236.486810 | 1953.562845 | 2552.979910 |

Dense+CE 的五轮 mean 均值=1773.0 ms、std=31.2；Hybrid+CE=1693.0 ms、std=273.6。两者在当前机器/诊断集上处于同一秒级量级；paired round mean delta=80.0±273.2 ms，范围 [-117.8,553.7]，不能把原单次约 80 ms 的差异写成可靠速度优势。没有剔除低/高延迟轮次；五轮很少，诊断样本也非全量 test，不做显著性夸大。

## 6. External Generalization：部分可测，端到端 BLOCKED

官方 SQuAD2 自然 Wikipedia 原文 + 原生人工 QA/gold，15 个不同文章摘录、75 问（45/30），未使用模型生成 gold、未修改 native questions。PDF 是原文格式转换，全部页渲染和 gold spans 验证完成；external 与原虚构 corpus 独立。全文/source hash 与原生 aliases 已保留。检索零调参完成：

| external R@1 | R@5 | MRR | nDCG@5 | positive N |
| --- | --- | --- | --- | --- |
| 1.000000 | 1.000000 | 1.000000 | 1.000000 | 45 |

完整生成在第一道题发生 Ollama 0.35.1 / Gemma2:9b CUDA 初始化失败；本项目服务按原二进制与参数重启后仍失败，共记录两次 API 错误。生成与 judge 的所有指标 N/A；API 失败不当作拒答或模型错误率。没有为完成表格换模型、库或重调参数，不宣称完成端到端外部验证。见 EXTERNAL_TEST_BLOCKED.md 与 external_test_report.md。

检索差值只是 descriptive cross-dataset generalization gap，不能归因为模型退化；15 个摘录并非完整企业政策，公开数据可能进入预训练，原 impossible 标签只有单段 annotation scope，多文档全局有效性仍待独立审核。

外测检索在当前小规模、主题分散的摘录集合上已饱和，不能外推为大规模困难检索性能；未单独测 Dense 外测，不能分离 CE 的外测贡献。

## 7. Final Claims 分级

| tier | claim | evidence / limits |
| --- | --- | --- |
| Strongly Supported | 现有 CE 在当前 V2 受控候选条件下大幅改善 Dense 排序 | R@1 +27.5pp；MRR +0.1739，paired CI 支持正收益；限定当前合成集，非严格总体证明 |
| Strongly Supported | 固定输入的重复排序稳定；候选构成可改变该实现分数/相对顺序 | 30题×2方法×5轮固定输入全一致；6题 composition probe 中2对固定 passages 翻转 |
| Strongly Supported | 当前 gate 没有取得 V2 端到端净安全收益 | 冻结 test FAR 0.025→0.025、FRR 0.0083→0.0333；保持 OFF，未重调阈值 |
| Supported with Caveats | Dense+CE 为当前更简单的最终选型 | 对 Hybrid+CE 有更高点估计，差值 CI 含0，不写显著优于或普适最优 |
| Supported with Caveats | 当前 K=10 未观察到 BM25 unique candidate rescue | 正式120正例中0例；不等同于所有预算/语料上 BM25 无价值 |
| Supported with Caveats | 两种重排方案在当前测量中延迟同量级 | 五轮随机方法顺序、30诊断题，不能断言约80ms为稳定算法速度差 |
| Supported with Caveats | 公开自然原文的零调参检索外测已完成 | 45正例/30原生impossible，限定摘录/原生scope；生成外测尚未完成 |
| Not Supported | Hybrid 提供 unique recall benefit / 显著优于或劣于另一方案 | 当前无 unique rescue，Dense+CE-Hybrid+CE CI包含0 |
| Not Supported | 当前 score gate 改善端到端安全 | FAR无下降且误拒答增加 |
| Not Supported | 已完成独立人工审核、自然企业端到端泛化或定位量化根因 | 人工pending；生成blocked；padding/quantization仅机制假说 |
## 8. 封版与复现

本轮可完成的自动验证已经结束；人工审核等待真实 reviewer，外部生成保留实际阻塞。项目封版，不再增加功能、启动 V3 或按 test 调参。简历与面试只使用 docs/final_resume_claims.md 中的支持范围。复现流程见 REPRODUCE.md，所有源预测 SHA、draw indices、replicate deltas、runtime/候选协议和失败日志保存完整。

新 clone 的原字节恢复使用既有 V2 快照与本轮五个未修改 legacy 文件的补充快照；Git 换行规范化差异已逐文件检查。原冻结工作目录禁止恢复写入。
