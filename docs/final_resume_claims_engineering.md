# TrustRAG：开发 / AI Engineer 简历版

- 基于 MIT 开源 RagBase 整理本地 PDF 问答流程，使用 FastEmbed/BGE、Qdrant、FlashRank、Ollama/Gemma2 与 Streamlit，实现页码/稳定chunk身份保留、会话隔离的文档上传、来源ID引用展示和明确拒答，保留上游署名与能力归属。
- 建立 config、固定dev/test、模型/文件SHA、逐题retrieval/generation/raw judge日志与checkpoint流程；完成240问合成V2诊断集、受控消融、10,000次paired bootstrap、五轮重复推理与随机方法顺序计时，支持只从保存预测重算指标。
- 根据实验选择 Dense+现有Cross-Encoder、Gate OFF、Citation ON；当前V2可回答test上R@1=95.83%、MRR=0.9792。保留失败、引用边界和负收益结果；通过单元测试、lint与冻结artifact验证，使实验、输出和资料来源可追溯。

## 可展开的工程点

共享RetrievalResult/chunk IDs、页码metadata、Qdrant本地索引、仅模型缓存与真实query embedding计时、输出引用ID检查、统一拒答、固定配置续跑、同指纹校验、只读重算、UTF-8资料与只在独立clone恢复原字节。

## 陈述限制

这是本地实验/演示项目，不是生产商业SLA或分布式平台；上游已有 parsing/chunking/Dense/Qdrant/FlashRank/LLM/Streamlit 并非原创。合成 benchmark、小类别样本、同模型族judge、人工PENDING与外部生成BLOCKED应如实解释；历史browser demo通过不表示当前GPU无故障。避免“降低幻觉”“显著优于Hybrid”“真实自然RAG100%准确率”等未经支持表述。
