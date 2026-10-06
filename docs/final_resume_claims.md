# TrustRAG 封版简历与面试陈述

## 可直接使用的项目描述

基于开源 curiousily/ragbase 构建可复现的检索增强问答评测与证据引用流程，设计包含语义改写、标识符、版本冲突等类别的 240 题合成诊断集，并完成冻结配置下的受控消融、失败分析和统计验证。

- 在独立 V2 test 的 120 道可回答题上，现有 Cross-Encoder 将 Dense 的 Recall@1 从 68.33% 提升至 95.83%，MRR 从 0.8052 提升至 0.9792；以 10,000 次 paired bootstrap 验证当前样本排序收益（MRR 差值 95% CI [0.1242, 0.2251]）。
- 通过 candidate rescue 和 reranker rank-change 分析评估组件价值：当前 K=10 下 BM25 unique rescue 为0；Dense+Reranker 相对 Hybrid+Reranker 的点估计更高，但 CI 包含0，因此选择更简单架构，保持实验对照配置。
- 对 30 道诊断题进行双方法五轮随机顺序实测：固定候选下 Top1/完整排名一致；另以固定 query/target/competitor 的候选构成实验复现两道 Top1 翻转，区分重复稳定与 batch 依赖。
- 使用来源 ID、页码与文本摘录支持引用核查；实测发现原 relevance-score gate 未降低 FAR 且增加误拒答，将默认 gate 关闭并保留原实验证据。

## 必须随陈述保留的边界

上述数值仅适用于合成 V2 诊断集，不写生产准确率或自然企业普适性能。每类 test 正例约20题，数据和 gold 由项目编写者共同构建，独立人工审核仍 PENDING_HUMAN_REVIEW。

公开 SQuAD2 自然文本检索外测已零调参执行：15个文章摘录、75个原生人工问题（45可回答），R@1=1.0000、MRR=1.0000。外部生成/judge 因原本地 CUDA 运行时错误 BLOCKED，不引用尚未测得的自然外测生成准确率/FAR，也不宣称自然企业端到端泛化已证实。

五轮测量显示两种重排方案在同一秒级量级，不能把单次80ms差异宣传成可靠提速。动态 padding / ONNX quantization 仅为 batch effect 的机制假说。

## 面试中不能说

- “显著优于 Hybrid+Reranker”或“证明 Dense+CE 普适最优”。差值 CI 包含0，选型同时考虑复杂度。
- “Hybrid 大幅提高召回”或“BM25在所有语料没有价值”。当前候选覆盖饱和，只报告该预算的0次 unique rescue。
- “gate显著降低幻觉/False Answer”或“score就是答案正确概率”。原 gate 没有净收益。
- “人工审核通过/100% grounded/生产数据验证完成”。judge不是独立人工；自然生成外测未完成。
- “发明了 Cross-Encoder 重排算法”。FlashRank、embedding、PDF/Qdrant/Streamlit 等沿用上游/现成组件，贡献在工程改造、受控评测、诊断和证据支持的取舍。
- 把原版到 V1 的 dev 增益全部归因于 BM25/RRF/重排：那是分块、深度、metadata/pipeline 的联合变化，缺少单因素因果对照。

## 推荐的一句话结论

“我用冻结消融、paired bootstrap 和输入稳定性实验验证了现有重排器的排序收益；没有为技术栈保留缺乏净收益的 Hybrid/gate，并明确记录合成数据、人工审核和外测运行阻塞的限制。”

封版后只做简历整理、项目讲稿和面试准备，不开启 V3。
