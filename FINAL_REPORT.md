# FINAL_REPORT

记录日期：2026-10-06（Asia/Shanghai）。开发分支：`trust-rag`。正式实验代码 commit：`eeea01f`；完整代码摘要及模型、配置、数据校验记录在 `experiments/formal_test_freeze.json`。

工程实现、本地原版复现、正式评测与 UI 测试均已完成。独立人工审阅尚未完成；已交付 20 条审阅样本，并明确标注 Codex 语义复核身份。本报告不把自动 judge 或 agent review 当作人工 ground truth。

## 1. 实际完成了什么

- 原始 RagBase：使用真实 Edge 浏览器上传 PDF，跑通原版解析、分块、Qdrant、检索、FlashRank、本地生成与 UI；验证明确答案、语义匹配、无答案三类问题，保存实际回答与截图。
- 统一 YAML 配置；保留页面级文件名、页码、偏移，生成确定性 document/chunk ID，让 Qdrant 与 BM25 使用相同 chunk 身份。
- 实现 Dense、BM25、RRF Hybrid，以及原有 FlashRank 的可控重排集成。
- 实现来源编号、答案内引用、已知 ID 与缺失/无效 ID 检查；低证据直接拒答，原始输出保留供审计。
- 在 dev 上比较 top1、top3 mean、margin 并扫描门限；正式 test 前冻结所有设置。
- 固定 10 份 PDF、120 页、160 题（120 answerable / 40 unanswerable），dev 40 / test 120；提供可靠的 span-to-chunk 对齐和文件哈希。
- 完成原版 dev 基线、三种 chunking 消融、候选深度/RRF 小网格、五组受控 test 检索、六组生成条件（含 gate off）。
- 保存 720 条真实系统结果：612 次实际生成模型调用、488 次实际 judge 调用；拒答跳过模型的记录同样保留。没有运行时 mock 或虚构指标。
- 保存逐题检索、重排、生成、总耗时与 API token 计数，记录固定模型和硬件；本轮只用本地模型，未估造电力成本。
- 输出多标签失败分类 CSV/Markdown、20 条 Codex 语义复核记录和独立人工审阅样本。
- 完成新 Streamlit 界面：演示/上传知识库、检索模式、答案、文件页码引用、证据评分、拒答状态与会话隔离；真实浏览器验证引用、拒答、PDF 上传及重置，并检查截图。

## 2. 真实正式结果

完整五组表及计时见 `reports/comparison.md`，所有汇总来自保存的 prediction 文件。

| 指标 | 主方案 |
| --- | ---: |
| Recall@1 | 0.9778 |
| Recall@5 | 1.0000 |
| MRR | 0.9889 |
| nDCG@5 | 0.9918 |
| 相对 Dense MRR 的百分点变化 | +2.74 |
| Answer correctness（LLM judge，90 个 answerable，拒答记 0） | 0.9333 |
| Groundedness（LLM judge，仅 84 个发布答案） | 1.0000 |
| Citation Accuracy（84 个发布引用的 gold-source precision） | 1.0000 |
| 端到端 Answerability F1 | 0.9655 |
| False Answer Rate（0 / 30） | 0.0000 |
| False Refusal Rate（6 / 90） | 0.0667 |
| 检索 gate 独立 test F1 | 0.8901 |
| 在线总耗时 P50 / P95 | 2149.9 / 2474.1 ms |

## 3. 没有提升和不应夸大的结果

- 单独 Hybrid 的 MRR 为 0.9407，低于 Dense 的 0.9615；不能说 RRF 必然更优。
- gate on/off 的 FAR 均为 0。gate on 端到端 F1 为 0.9655，gate off 为 0.9944；门限增加了误拒答，没有测得误答率收益。保持预先冻结设置，不用 test 重新选择门限。
- gate dev F1 为 0.9508，其独立 test F1 为 0.8901，说明小 dev 集与相关性分数不能充分保证 answerability。端到端拒答还依赖生成提示及引用校验。
- 三种 chunking 的 dev 排序指标相同；按预定规则选择 Recursive，不宣传复杂 semantic splitter 的优势。
- 主方案有 6 个误拒答：5 个由 gate 导致，1 个来自模型拒答。该模型拒答涉及 q0305 的 Finance 角色表述歧义，原 gold 未更改。
- gate-off q0108 有一次 judge 输出 `{"answer`，无法解析；保留 raw output，计入 `judge_failure_count=1`，并从相应 judge 指标分母排除。没有将它填成正确标签。

## 4. 工程验证与复现

- 33 项单元测试通过，覆盖 RRF/BM25/Recall/MRR/nDCG 手算样例、metadata 偏移、threshold 包含边界、citation、低证据零 LLM 调用、seed API 合约、judge 严格 schema 与失败类型。
- Ruff 与依赖一致性检查通过；原 MIT LICENSE 未改。
- 六组正式结果均完成重算：指标与保存汇总完全一致，预测 SHA-256 保持不变。记录见 `reports/artifact_verification.json`。
- UI 验证：`docs/demo_ui_results.json`；截图在 `docs/demo_screenshots/`。原版证据在 `docs/baseline_ui_results.json` 与 `docs/baseline_screenshots/`。
- Windows 原始 PyStemmer 2.2.0.1 缺少 CPython 3.12 wheel；Phase 0 仅用官方 2.2.0.3 wheel 做兼容修复，原始源码和锁文件可从 upstream archive 恢复。后续项目有自己的更新锁文件。
- Setup 将 Poetry 工具环境放在 `.tools`，与项目 `.venv` 分开；当前工具依赖冲突也已修复。固定 BGE HF revision、FlashRank 文件 checksum、Ollama 0.35.1、Gemma 2 9B digest。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
.venv\Scripts\python.exe -m scripts.prefetch_models
.venv\Scripts\python.exe scripts/download_ollama.py --version 0.35.1
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1
.venv\Scripts\python.exe scripts/pull_local_model.py --model gemma2:9b
$env:HF_HUB_OFFLINE = '1'
.venv\Scripts\python.exe -m streamlit run app.py
.venv\Scripts\python.exe -m scripts.run_benchmark --output-root experiments/reproduction --phase all
.venv\Scripts\python.exe -m scripts.recompute_metrics experiments/hybrid_reranker
```

重复生成评测需要真实模型运行时间；只重算汇总不需调用模型。已完成正式实验不可覆盖，复现使用新目录。

## 5. 验收状态

- [x] 原版实际复现；upstream commit、独立分支与 MIT attribution。
- [x] 固定 corpus、dev/test 隔离、answerable/unanswerable、gold span alignment。
- [x] Dense、BM25、RRF、Hybrid、Reranker。
- [x] 完整 metadata、source-level citation、invalid ID 检查。
- [x] evidence features、dev threshold calibration、test F1/FAR/FRR。
- [x] Recall@K、MRR、nDCG、citation、生成 judge、失败分析、消融。
- [x] configs、真实实验工件、33 项测试、本地 Streamlit、可复现命令。
- [x] 20 条 Codex 逐条语义复核，复核者身份明确。
- [ ] 独立人工抽样审核：待审阅 `reports/review_samples.jsonl`，不能由本报告代为声称完成。

## 6. 局限与后续可复核工作

当前使用模板性、单事实、英语演示 corpus，达到第一版最低规模，尚未达到推荐的 200–300 个可回答、50–100 个不可回答问题的自然语料规模。不含 OCR、复杂跨页、多跳、多语或未见文档泛化验证。Judge 与 generator 使用同一模型族，标签可能有偏差；人工 audit 与自然企业文档 benchmark 是下一版本的重要工作。新上传文档的门限需要重新校准，界面明确显示域迁移状态。Groq 接口保留，但未做远程正式测试。

## 7. 文件与贡献追溯

- `docs/upstream_baseline.md` / `docs/baseline_reproduction.md`：原始能力、环境与真实复现。
- `docs/model_artifacts.json`：模型 revision/checksum、LLM digest、hardware。
- `reports/comparison.md`：正式检索、生成、gate 消融、性能。
- `reports/failure_analysis.csv` / `reports/failure_analysis.md`：分类、数量、代表样本、可能原因及改进。
- `reports/sample_review.md` / `reports/codex_sample_review.csv`：20 例语义复核与标注歧义。
- `docs/my_changes.md`：实际 Git 差异及 attribution；`docs/resume_material.md`：三条真实简历素材。
- 保留源项目 `LICENSE`。上游已有模型、框架与功能不被描述为原创。
