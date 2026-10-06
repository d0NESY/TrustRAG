# TrustRAG 最终复现入口

先阅读 [FINAL_PROJECT_REPORT.md](FINAL_PROJECT_REPORT.md)。正式 V1/V2、bootstrap、稳定性、延迟和外测检索都已冻结；本页区分只读重算与真实模型重跑，不能把复现命令当成重新调参许可。

## A. Environment

Python 3.12（原环境 3.12.7）；使用原依赖快照而不是随意升级。模型、版本、revision与SHA见 `docs/model_artifacts.json`。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r reports/v2/environment_requirements.txt
```

项目源码从根目录加载，不从PyPI获取替代ragbase包。初次下载原模型需要网络：

```powershell
.venv\Scripts\python.exe -m scripts.prefetch_models
.venv\Scripts\python.exe scripts/download_ollama.py --version 0.35.1
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1
.venv\Scripts\python.exe scripts/pull_local_model.py --model gemma2:9b
```

必须匹配记录的BGE revision、FlashRank文件SHA、Gemma2 digest和Ollama 0.35.1；不能改模型、量化、API或generation config绕过故障。`.runtime`模型权重不提交，按原来源取得并核验。当前本机生成环境可能仍BLOCKED，实际状态见release恢复记录。

### 新 clone 的原字节

Git规范化换行会丢掉部分旧mixed LF/CRLF；只在**独立新clone**内运行：

```powershell
.venv\Scripts\python.exe -m scripts.release.restore_bytes --restore
```

新release helper读取原V2与legacy字节快照，只恢复EOL差异、拒绝原冻结工作目录和语义变更，**保留用户本轮授权更新的README**。不要直接用旧helper整包恢复README，那是历史版本，和新总入口语义不同。当前项目使用不带`--restore`的只读检查。

## B. Demo

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1
$env:HF_HUB_OFFLINE = '1'
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

默认`Dense + 重排`，门限关闭，提供来源、页码、实际excerpt和拒答状态；加载的是`configs/demo/`，不是改写的V1正式配置。8501占用时可用8502等新端口。历史真实browser检查已经完成；当前CUDA故障会影响生成，不宣称每台机器无环境问题。

## C. Benchmark

原数据无需重新生成：V1 `data/benchmark/`；V2 `data/benchmark_v2/`。不同角色见manifest、aligned gold及冻结文件；当前builder在已存在manifest时拒绝覆盖。不要在发布目录重新校准/选参数或修改gold。

V2检索/生成复验都使用原算法与参数；安全入口只把原evaluator的输出重定向到`experiments/reproduction/`的新命名子目录。生成包括原G0/G1，不重新拟合阈值。

## D. Recompute Only（优先）

```powershell
.venv\Scripts\python.exe -m scripts.release.verify_artifacts --recompute
.venv\Scripts\python.exe -m scripts.release.restore_bytes
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check ragbase scripts tests --select F
```

只读取既有predictions，重算旧V1/V2、公开外测检索指标并对照原metrics，再从原rankings重算paired bootstrap数组；只写`reports/release/`核验报告。模型不会被调用，原metrics/predictions不会覆盖。不要直接运行旧`v2.analyze`或旧final-validation report builder来改写冻结报告。

## E. Full Rerun（真实本地模型，耗时更长）

```powershell
.venv\Scripts\python.exe -m scripts.release.rerun --output-root experiments/reproduction/v2_run01 --phase retrieval
.venv\Scripts\python.exe -m scripts.release.rerun --output-root experiments/reproduction/v2_run01 --phase gate
```

也可`--phase all`。入口拒绝正式目录或无命名子目录，只复用原V2 evaluator/配置，输出到明确新目录；不修改原程序参数、原checkpoint或原结果。同指纹可以续跑，完整checkpoint会跳过。新机器/功率/调度/cache状态可能改变latency或少量生成字句，必须区分新run identity。

V1既有安全输出入口：

```powershell
.venv\Scripts\python.exe -m scripts.run_benchmark --output-root experiments/reproduction/v1_run01 --phase all
```

统计/重复实验若需从头验证，在独立副本中归档原validation目录，不删除当前产物，按`reports/final_validation/REPRODUCE.md`协议复验。不在发布目录再运行会覆盖已有validation输出的统计builder。

External retrieval的PDF、原生QA/gold、原JSON source和SHA已保存，不需模型生成gold。外部生成恢复只允许原冻结条件和本轮最多三次预算；本轮用完即停止，不自动无限重试。完整pipeline结果只有生成/judge全部75题完成才可标COMPLETE。

## Human Audit / 封版

真人优先填 `reports/release/human_audit_blind.csv`，四个人工字段为1/0/UNCERTAIN，notes自由解释，记录reviewer身份。填完运行 `python -m scripts.release.audit`，才生成comparison和人审最终汇总。目的性28条不是无偏test准确率估计；Codex与judge不能代填。

最终清单见 `reports/release/final_artifact_manifest.json`；原输入SHA不一致立即停止，不静默再生。最终commit记录见release summary/receipt及Git历史。封版后不启动V3，不新增方法、换模型、调test；只进入学习、讲稿与面试。
