# 最终验证复现与封版

本轮基于已冻结交付 `c0eaa39`，新分支 `trust-rag-final-validation`。所有原 V1/V2 产物、配置、数据与推理代码保持原字节；新数据和观察脚本没有引入新的检索算法。

## 环境与 clone 字节一致性

沿用 V2 的 Python 3.12.7 和固定依赖快照 `reports/v2/environment_requirements.txt`，模型校验和见 `docs/model_artifacts.json`。本轮实际运行环境另存 `experiments/final_validation/runtime_environment.json`。

新 clone 的 Git 换行规范化会改变 13 个旧文本文件的原字节。原 V2 快照覆盖其中 8 个，本轮额外快照仅保存另外 5 个未修改的 legacy 源文件。**只在独立 clone** 中依次执行：

```powershell
.venv\Scripts\python.exe -m scripts.v2.byte_snapshot --restore-line-endings
.venv\Scripts\python.exe -m scripts.final_validation.frozen_bytes --restore-line-endings
```

两种恢复都复用原有的严格校验：拒绝原冻结工作目录，拒绝二进制差异或语义修改，只恢复 LF/CRLF 的字节差异。当前目录不应执行恢复写入；可以运行 `python -m scripts.final_validation.frozen_bytes` 作只读检查。

## 重算统计与汇总已有结果

```powershell
.venv\Scripts\python.exe -m scripts.final_validation.bootstrap
.venv\Scripts\python.exe -m scripts.final_validation.human_audit
.venv\Scripts\python.exe -m scripts.final_validation.final_checks
.venv\Scripts\python.exe -m scripts.final_validation.report
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check scripts/final_validation tests/test_final_validation.py --select F
```

Bootstrap：10,000 次，seed=20261006；同一次 replicate 的 question indices 对所有方法一致。主问题级分析只含全部 120 answerable V2 test questions，另做家族整组敏感性分析。NPZ 保存抽样索引与每次差值，JSON 保存 source predictions SHA256、NumPy/RNG 与排序指标定义。报告生成器从原 rankings 再算两种 replicate 数组，不能用分别估计的 CI 代替 paired difference CI。

Human audit：CSV 人工字段初始全空，28 条目的性样本。只有真实独立 reviewer 填入 1/0/UNCERTAIN 与 reviewer_id 后，汇总才可报告已审核。测试代码中的临时人工标签只是 unit-test fixture，不属于真实审核。旧 V1 模板和所有正式结果不写入。

## 实际重复推理

```powershell
.venv\Scripts\python.exe -u -m scripts.final_validation.repeatability
.venv\Scripts\python.exe -u -m scripts.final_validation.batch_effect
```

使用原模型与原代码，先核验 runtime/model checksum。repeatability 的 30 题按预存 drift 及版本/标识符/语义类别选定，5 轮随机方法顺序，seed=7102026；每轮每方法有 2 次完整热身。300 个真实 timed queries 同时供稳定性和延迟分析。每次候选顺序和 ID 与正式列表比较；没有 cached query embeddings。

`repeatability` 已完整保存的 method block 会跳过。要从头复验，请在独立副本中归档相应 validation 子目录并区分 run identity，不删除当前结果。GPU/CPU功率状态、后台负载与调度会影响新测 latency，不能要求新机器毫秒值逐位相同。

Batch effect：六道诊断题；A/B/C 同 size10，target/competitor 文本和位置固定，其他8项改变；single-pair size1 为离线观察条件，生产预算保持10。每种条件三次，原始 tokens/padding/score/rank/top-k 保存。不改 live tokenizer，仅克隆 tokenizer 用于未截断长度观察；padding/quantization 具体原因未做归因实验。

## External source 与实际阻塞

真实 source 为官方 SQuAD2 development JSON，下载 URL、SHA 与完整 native QA/answers 保存于 external 目录。固定选择 15 个文章家族的自然首个合格摘录，每个3 positive/2 impossible，共75题；无结果过滤、无重新生成QA。15份PDF是原文格式转换，全部原文、gold offset、页数和渲染已验证；并非原始公开PDF，也不属于模拟政策文档。

```powershell
.venv\Scripts\python.exe -u -m scripts.final_validation.external_evaluate --retrieval-only
```

检索部分75题已完整完成，可从 predictions 重算45个正例指标。生成/judge 被 **Ollama 0.35.1 / 原 Gemma2:9b CUDA shared-object 初始化失败** 阻塞；相同服务按原二进制/参数重启后仍失败，两次错误和日志证据保留。原模型、算法参数、CUDA后端未替换；没有用API错误伪装模型拒答。

原 GPU 运行环境恢复后，可以在同一冻结外测指纹下续跑：

```powershell
.venv\Scripts\python.exe -u -m scripts.final_validation.external_evaluate
```

当前没有任何自然外测生成指标。不要把完整外测标为 COMPLETE。公开 benchmark 可能出现在预训练，impossible 标签是原单段 scope，后续真实人工 audit 如发现错误，应单独记录而非改本次 gold。当前 report driver 是本轮 BLOCKED 状态的封版汇总；若未来真完成生成，必须依据真实新结果重新汇总，不能继续发布旧 blocked 汇总。

索引是可重建运行缓存，不作为冻结正式输入；依靠固定PDF、配置、模型和源码重建。runtime 原始服务日志留在本地，提交中包含两次结构化执行错误与安全摘录的 CUDA 错误证据。

## 封版边界

自动可运行检查均已完成，人工审核 PENDING，外部生成 BLOCKED。`FINAL_VALIDATION_REPORT.md` 与 `docs/final_resume_claims.md` 区分强支持、带限制支持和不支持的陈述。停止 TrustRAG 功能开发；之后仅进入简历、项目讲稿和面试准备。
