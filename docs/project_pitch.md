# TrustRAG 项目讲稿

## 30 秒

我基于开源RagBase做了一个可评测的RAG项目，重点是检索排序、来源引用和失败分析。V2有240道合成诊断题，按政策家族隔离dev/test。现有Cross-Encoder把Dense的test Recall@1从68.33%提高到95.83%，paired bootstrap支持当前样本收益。Hybrid没有最终净优势，score gate还增加误拒答，所以最终选Dense+Reranker、gate关闭、citation保留。数据、人审和外测未完成部分都明确披露。

## 2 分钟

最初RagBase已经能上传PDF，做分块、Qdrant Dense检索和FlashRank重排，也有LLM和Streamlit。我没有把这些说成自己发明，而是补上可复现评测、稳定chunk身份、页码引用和拒答追溯。

V1将Demo变成五组检索/生成可比较的实验系统。但R@5很快饱和，难以解释Hybrid价值，于是冻结V1再构建V2：240道合成问题，覆盖改写、标识符、hard negative、数字、版本冲突、附件选择和近似相关但缺事实的拒答题，按整个政策家族划分。

V2所有方法共用chunks/模型，候选和final深度10、context5。Dense+CE达到R@1 95.83%、MRR0.9792，Dense是68.33%/0.8052。10,000次paired bootstrap直接重采样同一题的两方法差值，MRR增益CI约[0.1242,0.2251]。

负结果更影响架构。BM25在当前K10没有unique rescue；Hybrid+CE只有更低点估计，但CI包含0，不能说显著劣于。gate没有降低FAR，反而让FRR升到0.0333，所以默认关闭。

最终是Dense+现有CE、Gemma2与引用核验。Citation只能帮助核对来源，不保证每条claim或所问事实都正确。独立人工audit仍pending，自然外测只完成小规模检索sanity check，生成存在运行时阻塞。我把这些限制保留，而不是加更多组件追数字。

## 5 分钟

### 1. 出发点与上游

项目基于MIT开源RagBase，其Dense、PDF解析、分块、Qdrant、FlashRank、LLM和UI已经存在。原复现先跑通上传到回答，再冻结source和原dev结果。新增贡献是受控实验与可核对的证据流程，不是新检索算法发明。

### 2. Benchmark与可复现性

V1是可评测化，但单页单事实、模板性强且R@5饱和。V2升级为180 answerable/60 near-miss共240问，dev80/test160，六个正例类每类test20。按document family隔离，并检查问题、template与span重叠。仍是Codex合成情景，没有独立人工gold验证；检查零字符串重叠不证明完全不存在语义关联。

共享corpus/chunks/model/candidate10/final10/context5，是受控比较的基础。所有原输出、失败、judge、配置和SHA保留；不能看到test后调参数、换gold或丢失败。

### 3. Reranker的收益

Bi-Encoder便于索引大量文档，Cross-Encoder联合读query+passage，计算更贵但能纠正前10内排序。Dense R@1 0.6833、MRR0.8052，加入现有CE后0.9583/0.9792。原候选池不变，所以可把该对照的增益归为重排贡献；没有进候选池的事实不能由重排补回。

paired bootstrap复用同一题ID抽样，10,000次的R@1增益CI为[20.0,35.83]pp、MRR为[0.1242,0.2251]。这支持当前冻结合成test收益，不是普适证明。

### 4. Hybrid与Gate的负结果

BM25适合词面/ID，Dense适合语义，所以先用RRF研究互补。当前Dense候选R@10已1，BM25unique rescue0；Hybrid无CE时early ranking确有改善，但Hybrid+CE没有比Dense+CE更高最终点估计。领先区间含0，选更简单方案，不宣传统计胜利。

gate把相关性score当门限，但相关主题不代表存在指定事实。rail案例问客户身份，系统引用了高相关的高管车票规则，仍答非所问；相反，三道低分可回答题已有完整gold，却被门限拦截。FAR0.025不变，FRR0.0083→0.0333，默认OFF。

### 5. Citation与稳定性

source ID绑定文件、page、chunk、实际excerpt；结构合法性和gold-source precision不是claim entailment。judge与generator同模型族，有偏差，真人audit不能用Codex代填。

30诊断题、双方法5轮同候选排名全一致。另固定query/target/competitor，只改其他八项batch，两对相同passage会次序翻转。证明batch影响当前实现，但padding/量化根因仍是假说。五轮随机方法顺序计时显示两方案秒级同量级，小样本80ms差不能当稳定性能优势。

### 6. 最终取舍和局限

选Dense+CE、原Gemma2、Citation ON、score gate OFF。小规模自然SQuAD2摘录检索sanity check完成，45正例Top1都命中，但不足以证明自然企业端到端泛化；生成未恢复时明确BLOCKED，人工pending。架构简化的理由是现有证据与维护成本，而不是故意放弃技术栈。之后不启动V3，只用该项目学习与准备面试。
