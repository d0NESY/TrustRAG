# TrustRAG V2 复现

在项目根目录使用 PowerShell、Python 3.12。V2 源码提交、运行参数、模型 checksum 和数据 checksum 均保存在 `experiments/v2/*/resolved_config.json` 与 `formal_v2_freeze.json`。不要覆盖任何 V1 文件。

## 环境

现有 `.venv` 已安装项目及评测依赖。`runtime_environment.json` 与 `environment_requirements.txt` 保存本次 Windows / Python 3.12.7 的实际依赖版本快照。新机器可先创建 Python 3.12 venv，使用 `python -m pip install -r reports/v2/environment_requirements.txt` 安装，再从项目根目录运行 module 命令；本地 ragbase 包从当前源码加载，不从 PyPI 获取。同样可使用项目 `poetry.lock` 初始化环境，并以实际快照核对最终版本。ReportLab 4.2.5 用于 PDF 构建，Playwright 1.51.0 用于 demo smoke 检查。

模型缓存位于 `.runtime`，不提交模型大文件。对照 `docs/model_artifacts.json` 获取并核验固定 BGE、FlashRank 与 Gemma2:9b。Ollama 固定 0.35.1，Gemma2 digest 为 `ff02c3702f322b9e075e9568332d96c0a7028002f1a5a056e0a6784320a4db0b`；BGE revision 为 `199291fdd1aa89faf9c20b722dc72ad5e17aa0d0`。已有脚本 `scripts/prefetch_models.py`、`scripts/download_ollama.py`、`scripts/pull_local_model.py` 可获取缓存，但不要重新写入 V1 provenance 文档。

## 新 clone 的字节一致性

V1 部分源文件混用 LF/CRLF，Git 的 `text=auto eol=lf` 规则会规范化换行，因此仅 Git commit 不足以恢复混合换行的原字节 SHA-256。`experiments/v2/v1_byte_snapshot.zip` 额外保存 262 个 V1 文件的原字节（含原保护清单及现有 V1 文档）；归档 checksum 和各文件 checksum 在 `v1_byte_snapshot_manifest.json`。原项目未修改任何这些文件。

仅在**独立新 clone** 中，环境准备好后执行：

```powershell
.venv\Scripts\python.exe -m scripts.v2.byte_snapshot --restore-line-endings
```

工具先验证整个归档 checksum，逐一检查全部目标位于该 clone 且差异仅为 LF/CRLF；在全部检查成功后恢复原字节。它拒绝改动最初冻结工作目录，拒绝二进制差异、缺失文件和语义/指标变更。当前项目只运行不写文件的 `python -m scripts.v2.byte_snapshot` 校验即可。

`.gitattributes` 保留原有默认换行与 PDF/PNG/JPG/ONNX/GGUF 二进制规则，只追加 ZIP 和新增 V2 数据、配置、脚本、结果与人工审阅模板的字节保留规则；它没有改写 V1 原文件。

## 验证与分析已有结果

```powershell
.venv\Scripts\python.exe -m scripts.v2.freeze_v1
.venv\Scripts\python.exe -m scripts.v2.analyze --phase all
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check scripts/v2 tests/test_v2.py --select F
```

`freeze_v1` 在 manifest 已存在时只核验；不重新冻结修改后的 V1。分析器核对完整题目 ID、类别、gold booleans、相同重排候选池、分数 features，并逐组精确重算 metrics。它只从预测文件生成 `reports/v2/`，不调用模型、不调参数、不写 V1。

## 实际模型运行

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1
.venv\Scripts\python.exe -u -m scripts.v2.evaluate --phase all --split both
.venv\Scripts\python.exe -m scripts.v2.analyze --phase all
```

现有完整 checkpoint 会跳过，不重复覆盖实测 latency。中断后仅允许在配置、索引和数据指纹一致时续跑。已经看过 test，不能重新调参后续写同一次实验。

如需从头验证模型预测，在单独 clone/复制目录中保留 V1 与冻结 V2 数据/配置，把已有 `experiments/v2` 作为只读参考归档，使用新的实验目录副本执行；不要删除或覆盖当前正式产物。新 run 的 latency、token cache 与硬件调度可能不同，必须单独归档并区分运行身份。

## 数据构建记录

`scripts/v2/benchmark_specs.py` 包含 30 个评测前编写的政策家族；`build_benchmark.py` 使用 seed=173 分配整个家族 dev/test，并生成确定性 PDF。当前数据已冻结，builder 在 manifest 存在时拒绝覆盖。需要验证构建确定性时，在独立新副本中先归档 `data/benchmark_v2`，而非在正式项目删 gold。

五组检索共享 chunks/corpus/model；每分支 K=10、融合 K=10、final K=10、context top5、RRF k=60。不把最多 20 项原始分支并集作为正式候选深度。G0/G1 只改变 V1 gate flag，门限保持原 top1=0.03984235227108002。

数据为 Codex 编写的合成情景，未使用被评测 Gemma2 生成 gold；不称为独立人工数据或自然企业 benchmark。人工审阅模板仅供真实独立 reviewer 填写，当前状态 `PENDING_HUMAN_REVIEW`。

## Demo

```powershell
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
.venv\Scripts\python.exe -m scripts.v2.check_demo
```

demo 只读取 `configs/demo/`，门限默认关闭。V1 `configs/*.yaml` 与 V2 对照 `configs/v2/*.yaml` 保留原实验身份。新 demo smoke 产物写入 `reports/v2/`，不覆盖 V1 截图/检查记录。

本次浏览器验证使用独立端口 8502；对应命令为 `python -m scripts.v2.check_demo --url http://127.0.0.1:8502`。这样保留已有演示会话，同时验证当前分支代码。
