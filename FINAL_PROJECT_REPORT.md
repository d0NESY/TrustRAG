# TrustRAG 最终项目报告

这是整个项目后续阅读的统一入口。原 V1、V2 与最终验证报告保留为冻结的历史证据；本报告汇总已有真实结果，不重写正式实验。当前主方案为 **Dense + Existing Cross-Encoder Reranker，Gate OFF，Citation ON，Gemma2:9b**。

## 1. 项目背景

项目基于 MIT 开源 [curiousily/ragbase](https://github.com/curiousily/ragbase) 二次开发，上游作者 Venelin Valkov，原始提交 `5af7b79162329fa0b725b39d1aeeea7eb1e4428b`。目标是把 PDF 问答 Demo 变成有固定数据、可复核来源、受控比较和可重算指标的 RAG 实验项目，不宣称完全原创或生产商业系统。

## 2. Upstream RagBase 已有能力

原项目已有 PDF parsing、Semantic/Recursive chunking、FastEmbed/BGE、Dense retrieval、Qdrant、FlashRank、LLM/Ollama/Groq、Streamlit 与对话历史。Cross-Encoder 与这些工具不是本项目发明。原版上传、解析、检索、生成和 UI 已实际复现，源码冻结与兼容记录见 [baseline reproduction](docs/baseline_reproduction.md)。

## 3. 本项目新增工作

- Benchmark construction 与文件/page/span/chunk ID 对齐，保存输入和模型 SHA。
- 同 corpus、chunks、模型和候选预算的 Dense/BM25/Hybrid/Reranker 受控实验，BM25/RRF 作为实验能力保留。
- source ID、页码、引用摘录、引用合法性校验、真实拒答与原始输出追溯。
- Answerability evaluation、gate on/off 消融、near-miss、rescue/rank-change 与 Failure Analysis。
- V2 Hard Benchmark、paired bootstrap、固定输入稳定性、candidate batch composition、随机顺序 latency repeatability。
- 原生公开数据的 external retrieval sanity check，以及基于证据的架构简化。

## 4. V1：从 Demo 到可评测系统

V1 为虚构 Northstar 政策：10 个 PDF、120 页，160 问（40 dev、120 test；全量120可回答/40不可回答）。保留页码、稳定身份，建立五组受控检索和生成/引用/拒答指标。

正式 V1 test 已冻结：Dense R@1=0.9333、MRR=0.9615；Dense+CE 0.9667/0.9833；Hybrid+CE 0.9778/0.9889，主要方案 R@5 都已饱和。gate ON 的 FAR=0、FRR=0.0667；OFF 的 FAR=0、FRR=0.0111。完整旧结果见 [V1 comparison](reports/comparison.md)，不再在 V1 test 上选择参数。

原版到 V1 dev 的变化同时包含分块、候选深度、metadata/索引与 gold 对齐，不能把巨大 dev 提升全部归因于 BM25/RRF 或重排。原版 FlashRank 本身已存在，最终比较用统一条件区分其排序贡献。

## 5. V2：Hard Benchmark 与主要结果

240 道**合成诊断问题**：180 answerable、60 near-miss。dev80（60/20）、test160（120/40），30个政策家族、90份PDF、180页，按整个家族划分 dev/test。六种正例类别为 semantic、exact-term、hard-negative、numeric/date、version-conflict、cross-document，test每类20题。

事实、问题和 gold 由 Codex 在评测前共同编写，未由被评 Gemma2 生成 gold，也不称为独立人工数据或自然企业 QA。字符串/template/family/span/near-duplicate 检查完成，但不能证明不存在所有语义模板关联；部分 cohort hard-negatives 同页，同 chunk 命中不能证明页内事实区分。候选 R@10 仍饱和，难度主要增加在 early ranking 与版本/拒答边界。

所有组使用原 BGE `BAAI/bge-base-en-v1.5`、`ms-marco-MiniLM-L-12-v2`、Recursive/page-preserving 2048/128；分支/融合候选K=10，保存final10，生成context top5；原 RRF k=60。没有看 test 后调参数或删除失败题。

| Method | Recall@1 | Recall@5 | MRR |
| --- | ---: | ---: | ---: |
| Dense | 68.33% | 96.67% | 0.8052 |
| Dense + Reranker | **95.83%** | **100%** | **0.9792** |
| Hybrid | 80.00% | 99.17% | 0.8873 |
| Hybrid + Reranker | 94.17% | 100% | 0.9708 |

上述 ranking 仅统计 V2 synthetic hard benchmark 的 **120 answerable test questions**。当前 controlled benchmark 中，Cross-Encoder 是主要有效排序增强组件；不是自然生产准确率。

### Hybrid 与 BM25

Hybrid+CE 相对 Dense+CE：R@1 delta=-0.0167、MRR delta=-0.0083。反向差值的 bootstrap CI 包含0，因此只能说 Dense+CE 具有较高点估计并且架构更简单，不能说显著优于。

当前 V2 K=10：BM25 unique candidate rescue=0，Dense rescue=2。结论依赖 dataset、budget、chunking、embedding 和 query distribution，不能说 BM25 没用。Hybrid 在不重排时改善 Dense 的 early ranking，但没有在最终重排后提供净质量优势。

### Gate 与 Citation

| V2 condition（同 Hybrid+CE 检索） | FAR | FRR | Answerability F1 |
| --- | ---: | ---: | ---: |
| Gate OFF | 0.0250 | 0.0083 | 0.9917 |
| Gate ON | 0.0250 | 0.0333 | 0.9789 |

当前 relevance-score gate 没有减少 False Answer，却增加 False Refusal，因此默认 OFF，只保留 experimental ablation。score 是相关性，不是所问事实存在性或答案正确概率。高分的 rail near-miss（top1≈0.9776）仍把员工群体车票规则当成客户身份答案；三道 gate 新拒答的 gold 已在所给摘录中。

Citation 保留：每个 source ID 映射 filename、page、chunk 和实际 excerpt。ID 校验只检查引用结构；gold-source citation precision 是 **source-level attribution metric**，不是 claim-level entailment correctness。grounded statement 仍可能答非所问。固定 Gemma judge 可出错且与 generator 同模型族，未获得独立人工验证。

## 6. 最终可信度验证

120 个 answerable V2 test ID 的 paired bootstrap：10,000 replicates，seed=20261006，同一次抽样所有方法共享 ID，直接计算指标差值。

| Dense+CE − Dense | Point delta | 95% percentile CI |
| --- | ---: | --- |
| Recall@1 | +27.5 pp | [+20.0, +35.83] pp |
| MRR | +0.1739 | [+0.1242, +0.2251] |

Paired bootstrap supports a robust positive ranking gain on the frozen V2 test set；区间不是严格统计学证明。Dense+CE − Hybrid+CE 的 MRR CI=[0,0.0208]、R@1 CI=[0,0.0417]，均包含0。另做家族 cluster sensitivity analysis，未把 P(delta>0) 当 p-value。

30道诊断题、两个方法各五次、300次实际查询：固定候选下score std=0、完整排名和Top1重复agreement=100%。6题A/B/C/single-pair构成实验中，两对固定target/competitor改变其他候选后出现次序/Top1翻转；padding/量化根因仍为 mechanism hypothesis。

五轮随机方法顺序、每方法两次热身：Dense+CE mean≈1773±31ms，Hybrid+CE≈1693±274ms；paired轮均值差≈80±273ms，两种方案同量级，不能宣传稳定80ms提速。诊断查询集不代表全量分布。

External natural retrieval sanity check **COMPLETE**：公开 SQuAD2原生人工QA/gold，15篇不同文章的自然摘录、75问（45正例/30native impossible），原文忠实转换PDF，不是模拟政策。45个正例R@1/R@5/MRR/nDCG均1.0；小且主题分散的摘录不能外推为真实自然文档100% RAG准确率。原负例是单段scope，公开数据可能进入预训练，生成和语义引用仍需单独评估。

Human Audit：**PENDING_HUMAN_REVIEW**。28条目的性盲审包放在 [human_audit_blind.csv](reports/release/human_audit_blind.csv)，不展示judge/自动系统标签，人工字段未由Codex代填。

External Generation：**BLOCKED**。本轮最多三次同冻结条件恢复，记录GPU/驱动、端口、原服务、模型digest、命令与实际错误；不换LLM/API/量化或修改generation参数。详细状态见 [恢复日志](reports/release/external_generation_recovery_log.md)。生成若仍BLOCKED，所有未测指标为N/A，API异常不冒充拒答。

## 7. 最终架构与状态

PDF Parser → Recursive/Page-preserving Chunks → BGE → Qdrant Dense Top10 → Existing Cross-Encoder → Top5 context → Gemma2:9b → grounded prompt/refusal + citation validation。

默认显式score gate OFF；Hybrid/BM25/RRF与gate仅保留实验配置。最终选型基于充分候选覆盖、明显重排收益、无unique lexical rescue、复杂度和误拒答代价，继续采用当前最简单有效方案。架构与度量边界见 [FINAL_ARCHITECTURE_DECISION](reports/release/FINAL_ARCHITECTURE_DECISION.md)。

- **COMPLETE**：原版复现、V1/V2、检索/重排实验、paired bootstrap、stability、latency、citation实现及其自动评测、external retrieval、测试、历史真实demo检查、artifact verification。
- **PENDING**：独立Human Audit，除非真实reviewer填完。
- **BLOCKED**：External generation，除非同冻结环境恢复完成。历史demo检查完成不保证当前故障GPU环境能生成。

## 8. 使用与封版

[README](README.md) 是首页概览；[REPRODUCE](REPRODUCE.md) 区分仅重算与实际模型重跑。原冻结报告继续留存，不能用本总报告改变原始结果。简历见 [算法版](docs/final_resume_claims.md)、[工程版](docs/final_resume_claims_engineering.md)，讲稿与防守题见 docs/。

本轮仅更新用户明确要求的README/简历文档，并添加release材料。最终SHA清单记录每个工件的path/size/type/frozen-new及原hash比较。项目正式封版，不开启V3、加Agent/GraphRAG、换模型或为了提高数字改benchmark；只用于学习、简历和面试。
