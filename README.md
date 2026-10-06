# TrustRAG

基于开源 [RagBase](https://github.com/curiousily/ragbase) 二次开发的 RAG 实验与引用问答项目。最终方案为 **Dense + Existing Cross-Encoder Reranker，Gate OFF，Citation ON**。统一阅读入口：[FINAL_PROJECT_REPORT.md](FINAL_PROJECT_REPORT.md)。

## Overview

按页解析PDF、保留metadata与稳定chunk ID，经BGE/Qdrant检索、现有FlashRank重排后提供Top5来源；Gemma2:9b使用grounding/refusal prompt，输出source ID引用并校验。所有实验保存逐题预测、原输出、指标与SHA，可重算。

## Why this project

把Demo转成可评测系统，并通过受控消融与失败分析选择简单、实验支持的架构。没有Agent、GraphRAG或训练，不声称生产商业系统。

## Architecture

`PDF → Page-preserving Recursive Chunks → BGE → Qdrant Dense Top10 → Cross-Encoder → Top5 Context → Gemma2:9b → Citation Validation`

默认分数gate关闭，提示词拒答与引用校验保留。[最终架构决策](reports/release/FINAL_ARCHITECTURE_DECISION.md)。

## Upstream RagBase

作者 Venelin Valkov；原始commit `5af7b79162329fa0b725b39d1aeeea7eb1e4428b`。PDF parsing、Semantic/Recursive chunking、FastEmbed、Dense/Qdrant、FlashRank、LLM和Streamlit是上游已有组件；保留MIT署名，不将它们称为原创算法。[实际复现记录](docs/baseline_reproduction.md)。

## My Contributions

Benchmark与span/chunk对齐；受控Dense/BM25/RRF/CE实验；来源ID/页码/引用摘录与拒答评测；Hard Benchmark、Failure/rescue/rank分析；paired bootstrap、稳定性/batch/延迟验证；公开自然文本检索sanity check；证据支持的架构简化。

## Benchmark

V2是**synthetic hard benchmark**：240问=180 answerable+60 near-miss，dev80/test160，30家族隔离，90PDF/180页，test每正例类20问。事实与问题由Codex在评测前共同编写，不是独立人工或自然企业QA；原gold不因结果修改。[数据边界](reports/v2/BENCHMARK_CARD.md)。

## Results

**Frozen V2 synthetic hard benchmark；120 answerable test questions**（另40 near-miss用于拒答评测）。

| Method | Recall@1 | Recall@5 | MRR |
| --- | ---: | ---: | ---: |
| Dense | 68.33% | 96.67% | 0.8052 |
| Dense + Reranker | **95.83%** | **100%** | **0.9792** |
| Hybrid | 80.00% | 99.17% | 0.8873 |
| Hybrid + Reranker | 94.17% | 100% | 0.9708 |

Dense+CE − Dense：R@1 **+27.5 pp**，95% paired-bootstrap CI **[+20.0,+35.83] pp**；MRR **+0.1739**，CI **[+0.1242,+0.2251]**。10,000 replicates。Paired bootstrap supports a robust positive ranking gain on the frozen V2 test set，非严格总体证明。

Dense+CE − Hybrid+CE 的CI包含0；选择更简单架构，不宣称显著优于。[V2明细](reports/v2/FINAL_V2_REPORT.md) / [最终可信度验证](reports/final_validation/FINAL_VALIDATION_REPORT.md)。

## Ablation

同语料/chunks/model，candidate/final10、context5，page-preserving Recursive2048/128。原RRF/门限的正式参数保留冻结。引用precision为gold-source attribution，非逐claim蕴含；LLM judge可出错。

## What did not help

- **Hybrid**：最终Hybrid+CE没有净质量优势，当前K10无BM25 unique rescue；不等于BM25在任何语料没用。
- **Answerability Gate**：同Hybrid+CE的V2 G0/G1中FAR均0.025；FRR0.0083→0.0333，F1 0.9917→0.9789。门限默认OFF。
- **Complex Semantic Chunking**：旧V1 dev小型消融三种方案MRR均1.0，未观察到稳定优势，按预定平局规则采用Recursive；不是在所有文档下否定语义分块。

## Reliability Validation

固定候选30诊断题×双方法×5轮，完整排名/Top1重复一致；batch对照复现2道固定passage pair翻转，padding/量化具体原因仍是假说。随机顺序五轮延迟两种方案同量级，不宣传单次80ms速度优势。

External retrieval sanity check完成：15个SQuAD2自然文章摘录/75原生人工问，45正例均Top1命中；小且主题分散，非100%自然RAG准确率。

**Human Audit：PENDING_HUMAN_REVIEW；External Generation：BLOCKED。** [盲审CSV](reports/release/human_audit_blind.csv) / [恢复记录](reports/release/external_generation_recovery_log.md)。未测生成指标N/A，不冒充真人审核。

## Demo

历史真实浏览器验证完成：引用回答、拒答、PDF上传、页码、清空会话。默认Dense+重排，gate关闭；当前GPU问题可能阻塞生成，历史检查不等于当前环境无故障。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

## Installation

Python3.12，原验证环境Windows3.12.7。模型/硬件与checksum在 [model_artifacts.json](docs/model_artifacts.json)，依赖快照在 [environment_requirements.txt](reports/v2/environment_requirements.txt)。Ollama固定0.35.1、Gemma2:9b原digest。完整步骤见 [REPRODUCE.md](REPRODUCE.md)；不升级/换模型绕过正式条件。

## Reproduction

优先只读校验和recompute-only，不调用模型、不覆盖旧metrics。Full rerun必须写独立新目录，会重新调用本地模型且耗时更长；同一冻结条件的有限外测恢复也保留全部错误。

```powershell
.venv\Scripts\python.exe -m scripts.release.verify_artifacts --recompute
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check ragbase scripts tests --select F
```

## Limitations

合成作者/模板偏差、每类小N；候选覆盖仍饱和；部分同页hard negative不能只用chunk命中判断事实区分；英语/自包含问题、无OCR；引用结构不保证语义支持；同模型族judge偏差；人工pending；自然小规模检索sanity check与预训练/annotation-scope限制；外测生成实际状态如上。

## License

保留上游 MIT [LICENSE](LICENSE) 与作者 attribution。模型、依赖和公开外测数据遵循各自许可（SQuAD2数据卡CC BY-SA4.0）；[外部来源卡](reports/final_validation/EXTERNAL_SOURCE_CARD.md)。

项目封版，不开启V3。后续只用于RAG原理学习、[简历](docs/final_resume_claims.md)、[讲稿](docs/project_pitch.md)与[面试防守](docs/project_defense_qa.md)。
