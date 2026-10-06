# TrustRAG 项目防守问答

所有数值限定冻结V2合成test与当前验证协议；恢复、人审实际状态以release材料为准。

## 1. 什么是RAG？

先从外部资料检索证据，再让生成模型依据所给证据回答。本项目保留检索、重排、context、输出与来源，能区分没找到、排错、截断、答错或拒答，RAG本身不保证无幻觉。

## 2. 为什么需要Embedding？

把文本映射到可比较的向量，使语义相近但措辞不同的query/document可以被检索。这里沿用BGE base en v1.5；英语、自包含问题是已验证范围，不能直接承诺中文等域表现。

## 3. Dense Retrieval是什么？

分别编码query和document，用向量相似度从Qdrant找候选。文档向量可离线索引，query向量在测量中实际重算；高相似度只代表相关性，不保证存在答案。

## 4. BM25是什么？

基于词频、逆文档频率和文档长度归一化的稀疏词面排序。常对明确术语、代码和名字有用；本项目在同一chunk身份上实现实验对照。

## 5. BM25和Dense有什么区别？

BM25依赖词面匹配，Dense通过预训练向量处理语义关联；两者都有数据和tokenization边界。不能把某个benchmark上的零rescue外推成BM25无用。

## 6. 为什么一开始做Hybrid？

希望词面与语义候选互补，并用受控实验判断是否真的带来unique evidence。研究目标不是必然保留组件；当前预算下Dense覆盖充分，因此最终词法分支缺少独有覆盖证据。

## 7. RRF是什么？

按各分支rank求和1/(k+rank)，避免直接比较BM25与cosine等不同分数尺度。V2保持原k=60，不看test调权重；分支10的并集最多20，但正式融合前10才是候选预算。

## 8. 为什么最后不用Hybrid？

当前K10无BM25unique rescue，Hybrid+CE没有更高点估计，维护词法索引和融合也增加复杂度。差值CI含0，所以说选更简单方案，不说统计上显著胜出；实验配置没有删除。

## 9. Reranker是什么？

对已经检索到的候选重新打分排序。本项目沿用上游已有FlashRank/ms-marco MiniLM L12，贡献在固定候选对照与诊断，不是发明模型。

## 10. Bi-Encoder与Cross-Encoder区别？

Bi-Encoder独立编码两边，便于预索引；Cross-Encoder联合处理query+passage，能做更细的匹配，但每个query都要对候选运行模型，不能直接复用独立文档向量。

## 11. 为什么Cross-Encoder更慢？

多次联合序列推理的成本高于向量搜索，所以只用前10候选。当前CPU五轮方案总计约1.7秒量级，不承诺生产SLA或稳定80ms方法差。

## 12. 为什么重排效果明显？

V2正确证据大多已进Dense前10，主要错误是early ranking，尤其版本、标识符和语义题。CE提升排序有明确受控证据；因候选池不变，它不能解决候选缺失。

## 13. Recall@1与Recall@5是什么？

前k中找回的相关chunk数除以gold相关chunk总数，按answerable问题平均。这里只有一个gold时等于是否命中；不可回答题不进入ranking指标，仍进入拒答与latency。

## 14. MRR是什么？

每题第一个相关结果rank的倒数取均值，未命中记0。当前保存深度10，MRR是截断定义，不能假设看过所有文档。

## 15. nDCG是什么？

相关结果按位置折扣，DCG再除理想DCG。当前是binary chunk relevance的nDCG@5，不是人工graded relevance或完整claim正确性。

## 16. 为什么V1升级Hard Benchmark？

V1模板单事实，R@5饱和，无法很好诊断Hybrid、版本排序或拒答。因此冻结V1，再用独立家族的V2去暴露early ranking与near-miss问题，不修改V1结果。

## 17. Near-miss unanswerable是什么？

知识库主题相关，但缺失问题指定的具体事实，比如未来年份价格或某客户身份。比明显无关问题更能检验相关性和事实充足性的区别。

## 18. Citation怎么实现？

按提供给模型的Top5实际excerpt分配S1等ID，绑定filename/page/chunk/offset，检查返回ID是否存在。保留raw输出；无效或缺失引用被拦截为拒答。

## 19. Groundedness是什么？

回答陈述是否得到提供证据支持。本项目固定judge评估，gold-source citation precision另算；结构ID合法、来源相关和语义蕴含是不同层次，不能互相代替。

## 20. 为什么grounded仍答非所问？

rail案例回答高管可头等舱这条有文本支持的规则，但问题问哪个客户。陈述可能grounded，仍没给缺失的客户身份；这也是不能用score或groundedness直接替代answerability的原因。

## 21. Answerability是什么？

当前材料是否足以可靠回答具体问题。评测用gold与实际发布/拒答状态：FAR=不可回答却发布的比例，FRR=可回答却拒答的比例。回答正确性还需要另查内容。

## 22. 为什么relevance不等于answerability？

相关主题/实体/词句可以高分，但缺失问到的时间、对象或数值。top1 AUC约0.963有整体信号，尾部仍有高分negative与低分positive，不能称为校准正确概率。

## 23. 为什么Gate关闭？

同Hybrid+CE的冻结V2 test：FAR均0.025，FRR从0.0083升到0.0333，F1下降。新误拒答3题gold已在摘录中，未观察到净收益，因此默认OFF且不再用test调门限。

## 24. Bootstrap为什么paired？

方法在同一组问题上测量，必须共享有放回抽样ID，直接估计两方法指标差值。分别算两组CI再看重叠会忽略题目内相关性；本项目10,000次、固定seed，另作家族cluster敏感性分析。

## 25. Bootstrap是否证明最优？

不是。对Dense的增益CI支持当前样本正收益；对Hybrid+CE差值CI含0，不写显著优于。P(delta>0)是resampling频率，不是p-value或总体优越性的后验概率。

## 26. 为什么架构越做越简单？

实验淘汰没有净收益的默认组件：候选覆盖已充分，CE排序有效，Hybrid无unique rescue且有维护成本，score gate增加误拒答。复杂度是取舍的一部分，而不是只追技术栈。

## 27. 为什么benchmark是synthetic？

便于控制事实、版本、gold spans和近似相关负例，保证实验可定位。但Codex共同编写事实/问题会有作者与模板偏差，所以显式标记synthetic，并准备独立真人audit和公开自然检索sanity check。

## 28. Synthetic benchmark有哪些风险？

问题与来源结构关联、难度偏低、每类小N、同页多个cohort让chunk命中不足以检验事实区分，字符串去重不能排除语义关联。不能把R@5饱和当作企业生产质量。

## 29. External test做了什么？

公开SQuAD2原生人工QA/gold；15个不同文章的原文摘录忠实转PDF、75问45正例。零调参检索45正例都Top1命中，但规模小主题分离；impossible只单段scope，公开数据可能进预训练，非100%自然RAG准确率。

## 30. 为什么external generation未完成？

历史原Ollama0.35.1/Gemma2 CUDA初始化失败；本轮最多三次环境恢复依然未恢复可执行生成，具体阶段和错误在release日志，不能把环境超时冒充模型错误。没有换模型/API/参数，未测指标N/A。

## 31. Batch composition为什么影响score？

直接实验确认固定query/target/competitor时仅改其他八项，两个pair会margin变号。固定候选五轮又完全一致。动态padding与量化是机制假说，未单因素归因，不能断言量化就是已证实根因。

## 32. Citation precision能保证逐claim正确吗？

不能。gold-source precision是source-level attribution代理，ID检查也只保证结构引用可定位。语义支持另用可出错judge，独立人工未完成时不宣称引用被真人验证。

## 33. 原版到V1提升是你算法功劳吗？

不能单独归因。原版拼页/整文档分块、候选5与FlashRank最多3输出，后续保页分块/候选10/gold对齐都改变。只有共享条件的V2对照可以更清楚归因当前排序组件。

## 34. 最终还有什么局限？

合成数据/小类别N、无OCR、英语自包含问题、context截断、版本/批次敏感性、同模型族judge、人审pending、自然生成blocked。最终保持Dense+CE/gateOFF/citationON，封版后不继续调test或开启V3。
