# External end-to-end test：BLOCKED

已取得真实公开 SQuAD2 数据，并冻结 15 个自然 Wikipedia 摘录、75 道原生人工 QA（45 positive / 30 impossible）。文档和 gold 来自官方数据，不是 Codex 生成的模拟数据。全部 PDF 原文、gold offset 和 15 页视觉转换已校验。

生成在第一道题触发 HTTP 500 / CUDA shared object initialization failed / llama-server exit 0xc0000409。已核实为本项目服务，按原二进制与启动参数重启后，同一题仍失败。两次失败全部保留在 experiments/final_validation/external/run/execution_errors.jsonl；服务日志另有恢复记录。

没有换模型、调参数、改 gold 或筛掉失败题。完整 75 道检索仍在既有 Dense+CE 上完成，但 **Answer Correctness、Groundedness、Citation Accuracy、Answerability F1、FAR、FRR 尚未测得，全部 N/A**。API 异常不冒充模型拒答，也不作为 0% 错误率。不能声称完成端到端自然文档泛化验证。
