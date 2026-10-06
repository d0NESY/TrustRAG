"""Resume variants, project pitches, and evidence-grounded interview answers."""

from scripts.release.common import ROOT, begin, verify, write_md


def main():
    begin()
    resume = """# TrustRAG：算法 / LLM 实习简历版

建议项目名：**TrustRAG：基于开源 RagBase 的证据引用与检索评测项目**。

## 三条可用描述

- 基于开源 RagBase 二次开发企业知识场景的 RAG 实验系统，构建包含语义改写、Hard Negative、版本冲突与 Near-miss 拒答的 **240 条合成困难诊断集**，建立检索、生成、来源引用和失败模式的可复现评测流程。
- 对 Dense、BM25、RRF Hybrid 与现有 Cross-Encoder 重排开展受控实验；最终 Dense+Reranker 在独立 V2 test 的 **120 个可回答问题**上达到 **Recall@1 95.83%、Recall@5 100%、MRR 0.9792**，相对 Dense 提升 **27.5 个百分点 / 0.1739 MRR**，以 **10,000 次 paired bootstrap** 支持当前样本的正排序收益（MRR差值95% CI [0.1242,0.2251]）。
- 完成 Citation、拒答、rescue/rank-change 与 Failure Analysis：当前 K=10 未观察到 BM25 unique candidate rescue，原 relevance-score gate 未降低 FAR（均0.025），FRR反而从0.0083升至0.0333；结合点估计、统计不确定性与维护成本，采用 Dense+Reranker、Gate OFF、Citation ON 的简化方案。

## 面试展开与必留边界

固定候选的30诊断题、双方法五轮重复排名完全一致；改变其他候选的batch试验复现2对固定passage的次序翻转。动态padding/ONNX量化仅为机制假说。

Dense+CE对Hybrid+CE点估计更高，但差值CI含0，不能写“显著优于”。FlashRank、BGE、Qdrant、PDF parsing/分块、LLM与Streamlit是沿用上游/现成组件；贡献在工程改造、受控评测、诊断与证据支持的取舍。

数据为合成且同作者构建事实/gold，每类test正例仅20，不能作为生产准确率。独立Human Audit仍PENDING；真实公开SQuAD2小规模自然检索sanity check完成（15摘录、45正例均Top1命中），不是100%自然RAG准确率。外部生成状态见release日志，未完成时绝不引用自然生成指标。

不把原版到V1的dev提升全归给检索算法：分块、深度、metadata和gold对齐共同变化。Citation precision为source归属代理；同模型族judge不是独立人工验证。CPU延迟五轮同量级，不宣传单次80ms稳定提速。

## 不使用的陈述

“完全原创算法”“生产级商业部署”“Hybrid大幅提升召回”“BM25没用”“gate降低幻觉”“独立人工验证通过”“自然文档100%准确率”“已证明量化根因”“显著优于Hybrid”。

封版后只学习RAG、整理讲稿和面试，不开启V3。
"""
    write_md(ROOT / "docs/final_resume_claims.md", resume)
    engineering = """# TrustRAG：开发 / AI Engineer 简历版

- 基于 MIT 开源 RagBase 整理本地 PDF 问答流程，使用 FastEmbed/BGE、Qdrant、FlashRank、Ollama/Gemma2 与 Streamlit，实现页码/稳定chunk身份保留、会话隔离的文档上传、来源ID引用展示和明确拒答，保留上游署名与能力归属。
- 建立 config、固定dev/test、模型/文件SHA、逐题retrieval/generation/raw judge日志与checkpoint流程；完成240问合成V2诊断集、受控消融、10,000次paired bootstrap、五轮重复推理与随机方法顺序计时，支持只从保存预测重算指标。
- 根据实验选择 Dense+现有Cross-Encoder、Gate OFF、Citation ON；当前V2可回答test上R@1=95.83%、MRR=0.9792。保留失败、引用边界和负收益结果；通过单元测试、lint与冻结artifact验证，使实验、输出和资料来源可追溯。

## 可展开的工程点

共享RetrievalResult/chunk IDs、页码metadata、Qdrant本地索引、仅模型缓存与真实query embedding计时、输出引用ID检查、统一拒答、固定配置续跑、同指纹校验、只读重算、UTF-8资料与只在独立clone恢复原字节。

## 陈述限制

这是本地实验/演示项目，不是生产商业SLA或分布式平台；上游已有 parsing/chunking/Dense/Qdrant/FlashRank/LLM/Streamlit 并非原创。合成 benchmark、小类别样本、同模型族judge、人工PENDING与外部生成BLOCKED应如实解释；历史browser demo通过不表示当前GPU无故障。避免“降低幻觉”“显著优于Hybrid”“真实自然RAG100%准确率”等未经支持表述。
"""
    write_md(ROOT / "docs/final_resume_claims_engineering.md", engineering)
    pitch = """# TrustRAG 项目讲稿

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
"""
    write_md(ROOT / "docs/project_pitch.md", pitch)
    qa = [
        ("什么是RAG？", "先从外部资料检索证据，再让生成模型依据所给证据回答。本项目保留检索、重排、context、输出与来源，能区分没找到、排错、截断、答错或拒答，RAG本身不保证无幻觉。"),
        ("为什么需要Embedding？", "把文本映射到可比较的向量，使语义相近但措辞不同的query/document可以被检索。这里沿用BGE base en v1.5；英语、自包含问题是已验证范围，不能直接承诺中文等域表现。"),
        ("Dense Retrieval是什么？", "分别编码query和document，用向量相似度从Qdrant找候选。文档向量可离线索引，query向量在测量中实际重算；高相似度只代表相关性，不保证存在答案。"),
        ("BM25是什么？", "基于词频、逆文档频率和文档长度归一化的稀疏词面排序。常对明确术语、代码和名字有用；本项目在同一chunk身份上实现实验对照。"),
        ("BM25和Dense有什么区别？", "BM25依赖词面匹配，Dense通过预训练向量处理语义关联；两者都有数据和tokenization边界。不能把某个benchmark上的零rescue外推成BM25无用。"),
        ("为什么一开始做Hybrid？", "希望词面与语义候选互补，并用受控实验判断是否真的带来unique evidence。研究目标不是必然保留组件；当前预算下Dense覆盖充分，因此最终词法分支缺少独有覆盖证据。"),
        ("RRF是什么？", "按各分支rank求和1/(k+rank)，避免直接比较BM25与cosine等不同分数尺度。V2保持原k=60，不看test调权重；分支10的并集最多20，但正式融合前10才是候选预算。"),
        ("为什么最后不用Hybrid？", "当前K10无BM25unique rescue，Hybrid+CE没有更高点估计，维护词法索引和融合也增加复杂度。差值CI含0，所以说选更简单方案，不说统计上显著胜出；实验配置没有删除。"),
        ("Reranker是什么？", "对已经检索到的候选重新打分排序。本项目沿用上游已有FlashRank/ms-marco MiniLM L12，贡献在固定候选对照与诊断，不是发明模型。"),
        ("Bi-Encoder与Cross-Encoder区别？", "Bi-Encoder独立编码两边，便于预索引；Cross-Encoder联合处理query+passage，能做更细的匹配，但每个query都要对候选运行模型，不能直接复用独立文档向量。"),
        ("为什么Cross-Encoder更慢？", "多次联合序列推理的成本高于向量搜索，所以只用前10候选。当前CPU五轮方案总计约1.7秒量级，不承诺生产SLA或稳定80ms方法差。"),
        ("为什么重排效果明显？", "V2正确证据大多已进Dense前10，主要错误是early ranking，尤其版本、标识符和语义题。CE提升排序有明确受控证据；因候选池不变，它不能解决候选缺失。"),
        ("Recall@1与Recall@5是什么？", "前k中找回的相关chunk数除以gold相关chunk总数，按answerable问题平均。这里只有一个gold时等于是否命中；不可回答题不进入ranking指标，仍进入拒答与latency。"),
        ("MRR是什么？", "每题第一个相关结果rank的倒数取均值，未命中记0。当前保存深度10，MRR是截断定义，不能假设看过所有文档。"),
        ("nDCG是什么？", "相关结果按位置折扣，DCG再除理想DCG。当前是binary chunk relevance的nDCG@5，不是人工graded relevance或完整claim正确性。"),
        ("为什么V1升级Hard Benchmark？", "V1模板单事实，R@5饱和，无法很好诊断Hybrid、版本排序或拒答。因此冻结V1，再用独立家族的V2去暴露early ranking与near-miss问题，不修改V1结果。"),
        ("Near-miss unanswerable是什么？", "知识库主题相关，但缺失问题指定的具体事实，比如未来年份价格或某客户身份。比明显无关问题更能检验相关性和事实充足性的区别。"),
        ("Citation怎么实现？", "按提供给模型的Top5实际excerpt分配S1等ID，绑定filename/page/chunk/offset，检查返回ID是否存在。保留raw输出；无效或缺失引用被拦截为拒答。"),
        ("Groundedness是什么？", "回答陈述是否得到提供证据支持。本项目固定judge评估，gold-source citation precision另算；结构ID合法、来源相关和语义蕴含是不同层次，不能互相代替。"),
        ("为什么grounded仍答非所问？", "rail案例回答高管可头等舱这条有文本支持的规则，但问题问哪个客户。陈述可能grounded，仍没给缺失的客户身份；这也是不能用score或groundedness直接替代answerability的原因。"),
        ("Answerability是什么？", "当前材料是否足以可靠回答具体问题。评测用gold与实际发布/拒答状态：FAR=不可回答却发布的比例，FRR=可回答却拒答的比例。回答正确性还需要另查内容。"),
        ("为什么relevance不等于answerability？", "相关主题/实体/词句可以高分，但缺失问到的时间、对象或数值。top1 AUC约0.963有整体信号，尾部仍有高分negative与低分positive，不能称为校准正确概率。"),
        ("为什么Gate关闭？", "同Hybrid+CE的冻结V2 test：FAR均0.025，FRR从0.0083升到0.0333，F1下降。新误拒答3题gold已在摘录中，未观察到净收益，因此默认OFF且不再用test调门限。"),
        ("Bootstrap为什么paired？", "方法在同一组问题上测量，必须共享有放回抽样ID，直接估计两方法指标差值。分别算两组CI再看重叠会忽略题目内相关性；本项目10,000次、固定seed，另作家族cluster敏感性分析。"),
        ("Bootstrap是否证明最优？", "不是。对Dense的增益CI支持当前样本正收益；对Hybrid+CE差值CI含0，不写显著优于。P(delta>0)是resampling频率，不是p-value或总体优越性的后验概率。"),
        ("为什么架构越做越简单？", "实验淘汰没有净收益的默认组件：候选覆盖已充分，CE排序有效，Hybrid无unique rescue且有维护成本，score gate增加误拒答。复杂度是取舍的一部分，而不是只追技术栈。"),
        ("为什么benchmark是synthetic？", "便于控制事实、版本、gold spans和近似相关负例，保证实验可定位。但Codex共同编写事实/问题会有作者与模板偏差，所以显式标记synthetic，并准备独立真人audit和公开自然检索sanity check。"),
        ("Synthetic benchmark有哪些风险？", "问题与来源结构关联、难度偏低、每类小N、同页多个cohort让chunk命中不足以检验事实区分，字符串去重不能排除语义关联。不能把R@5饱和当作企业生产质量。"),
        ("External test做了什么？", "公开SQuAD2原生人工QA/gold；15个不同文章的原文摘录忠实转PDF、75问45正例。零调参检索45正例都Top1命中，但规模小主题分离；impossible只单段scope，公开数据可能进预训练，非100%自然RAG准确率。"),
        ("为什么external generation未完成？", "历史原Ollama0.35.1/Gemma2 CUDA初始化失败；本轮最多三次环境恢复依然未恢复可执行生成，具体阶段和错误在release日志，不能把环境超时冒充模型错误。没有换模型/API/参数，未测指标N/A。"),
        ("Batch composition为什么影响score？", "直接实验确认固定query/target/competitor时仅改其他八项，两个pair会margin变号。固定候选五轮又完全一致。动态padding与量化是机制假说，未单因素归因，不能断言量化就是已证实根因。"),
        ("Citation precision能保证逐claim正确吗？", "不能。gold-source precision是source-level attribution代理，ID检查也只保证结构引用可定位。语义支持另用可出错judge，独立人工未完成时不宣称引用被真人验证。"),
        ("原版到V1提升是你算法功劳吗？", "不能单独归因。原版拼页/整文档分块、候选5与FlashRank最多3输出，后续保页分块/候选10/gold对齐都改变。只有共享条件的V2对照可以更清楚归因当前排序组件。"),
        ("最终还有什么局限？", "合成数据/小类别N、无OCR、英语自包含问题、context截断、版本/批次敏感性、同模型族judge、人审pending、自然生成blocked。最终保持Dense+CE/gateOFF/citationON，封版后不继续调test或开启V3。")]
    text = "# TrustRAG 项目防守问答\n\n所有数值限定冻结V2合成test与当前验证协议；恢复、人审实际状态以release材料为准。\n\n"
    text += "\n\n".join(f"## {number}. {question}\n\n{answer}" for number, (question, answer) in enumerate(qa, 1))
    write_md(ROOT / "docs/project_defense_qa.md", text)
    verify()
    print("Two resume variants, 30s/2min/5min pitch, and 34 defense answers written.")


if __name__ == "__main__":
    main()
