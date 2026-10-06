# TrustRAG Release Summary

**What was built?** 基于MIT开源RagBase的本地RAG实验与引用问答项目，加入benchmark、受控消融、可追溯引用/拒答、failure/rescue诊断、统计与复现工件；不是完全原创或生产商业平台。

**What was improved?** 当前V2 synthetic test 120个正例中，Dense→现有CE：R@1 68.33%→95.83%、MRR0.8052→0.9792。R@1增益27.5pp（95%paired CI [20.0,35.83]pp）；MRR增益0.1739（CI [0.1242,0.2251]）。

**What actually helped?** 当前候选覆盖充分时的Cross-Encoder排序；页码/chunk身份与source ID为可核对证据流程提供工程基础。

**What did not help?** 当前K10无BM25unique rescue；Hybrid+CE没有更高最终点估计，差值CI含0；score gate FAR不变且FRR上升；复杂semantic分块旧小型dev消融未显示稳定优势。不是普遍否定这些技术。

**Final architecture?** Dense/Qdrant Top10 + Existing Cross-Encoder + Top5 Context + Gemma2:9b + grounding/refusal prompt + Citation Validation；score gate OFF，Hybrid仅实验。

**Reliability?** 10,000 paired bootstrap；30题×双方法×5轮固定输入排名一致；batch probe 2次固定pair翻转，机制仍是假说；随机顺序5轮延迟同量级，不能宣传稳定80ms提速。

**Incomplete?** Human Audit PENDING_HUMAN_REVIEW（28条盲审字段未由Codex填写）；External generation BLOCKED（历史CUDA失败，本轮最多3次环境恢复仍未恢复，不换正式条件）。公开自然检索sanity check COMPLETE：15短文章摘录、75问中45正例Top1命中，非100%自然RAG准确率。实际状态以release日志/JSON为准。

**How to reproduce?** 统一入口 [REPRODUCE.md](../../REPRODUCE.md)，优先只读重算与SHA核验；Full Rerun使用独立新目录，真实调用本地模型，不覆盖正式产物。

**Reading entry?** [FINAL_PROJECT_REPORT.md](../../FINAL_PROJECT_REPORT.md)；README概览；docs里两版简历、三种时长讲稿与项目防守题。旧冻结报告全部保留。

**Release commit?** 最终提交由Git历史和 `release_commit_receipt.json` 记录；receipt是提交后的本地校验回执，不放入该提交以避免自引用hash。基线为 `126602ff35c86778eda192a5be3cc73a1606651a`。

项目正式封版，不开启V3或继续为提高数字改benchmark。
