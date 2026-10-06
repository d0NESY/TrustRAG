# 简历素材（仅使用真实完成内容）

## 项目标题

TrustRAG：基于混合检索、证据引用与可复现实验的企业知识库问答系统

## 三条 bullet

- 基于 MIT 开源 RagBase 二次开发企业知识库问答系统，新增按页 metadata、稳定 chunk ID、Dense/BM25 共享身份与 source-level citation 校验，使用本地 Ollama Gemma 2 9B 完成真实 PDF 上传和问答部署。
- 实现 Dense + BM25 + RRF，并接入上游 FlashRank 重排；固定语料、分块、embedding 与 Top-K 进行五组受控实验，在 90 个可回答 test 问题上将 MRR 从 Dense 的 0.9615 提升至 0.9889（+2.74 个百分点），Recall@5 为 1.0000。
- 构建 160 题 dev/test 隔离 benchmark、三类证据特征门限扫描，以及完整的预测重算和失败分析流程；主方案在 120 题正式 test 上达到 gold-source Citation Accuracy 100.0%、端到端 Answerability F1 0.9655，并公开误拒答与门限消融结果。

## 指标口径与面试说明

- 数据为 10 份虚构政策 PDF、单事实单页，含 120 个可回答和 40 个不可回答问题；dev 40、test 120。结果不能当作自然企业语料泛化能力。
- Citation Accuracy 是 gold-source precision，不能等同于逐 claim 人工验证。Groundedness 和正确性使用固定同模型族 LLM judge，可能存在偏差。
- 0.9655 是包含 gate、生成模型拒答与引用检查后的端到端 F1。检索 gate 单独的 test F1 为 0.8901。
- gate on/off 的 FAR 均为 0；关闭 gate 的端到端 F1 为 0.9944，优于 gate on。本轮门限增加误拒答，不能写成“门限提升拒答准确率”或“降低幻觉”。
- Hybrid 无重排的 MRR 低于 Dense；本轮提升由完整融合 + 重排方案取得，不应归因于 RRF 单独更优。
- 原始 PDF ingestion、semantic/recursive splitting、FastEmbed、Qdrant、FlashRank、Streamlit、LLM 和历史管理属于 upstream；贡献是新增、整合与评测，不是从零发明这些组件。
- 20 条样本由 Codex 逐条语义复核，发现一处 Finance 审核方表述歧义；独立人工审核仍待进行，未修改正式 test gold。

## 证据文件

`reports/comparison.md`、各组 `experiments/*/retrieval_predictions.jsonl`、`generation_predictions.jsonl`、`judge_results.jsonl`、`reports/sample_review.md`、`docs/my_changes.md`。
