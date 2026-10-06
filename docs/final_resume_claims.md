# TrustRAG：算法 / LLM 实习简历版

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
