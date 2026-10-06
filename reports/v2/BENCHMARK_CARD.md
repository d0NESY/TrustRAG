# Meridian Hard V2 数据说明

- Version：`meridian-hard-v2.0`，family split seed=173。
- 240 道英文问题：180 answerable、60 near-miss unanswerable。
- 30 个政策家族；每家族 1 份 current 2026 操作指南、1 份 superseded 2024 历史版本、1 份 reference annex。共 90 份 PDF、180 页。
- dev 10 家族、80 题；test 20 家族、160 题。家族内全部问题同 split。索引共享整个 corpus，监督题目与 gold 的文档家族隔离。
- 原始文本、事实清单、文档归属、问题 JSONL、PDF 与数据 manifest 都保存在 `data/benchmark_v2/`。

| Category | 目的 | dev/test |
| --- | --- | --- |
| semantic | 改写问法，减少问题与目标事实的词面重叠 | 10/20 |
| exact_term | 表单、代码、标识符与相邻编号干扰 | 10/20 |
| hard_negative | 相同主题下不同对象/资格/路线的相似事实 | 10/20 |
| numeric_date | 不同期限、金额、数量、日期的邻近干扰 | 10/20 |
| version_conflict | current 2026 与 archived 2024 的冲突 | 10/20 |
| cross_document | 在操作指南和控制附件间选择正确证据来源 | 10/20 |
| near_miss_unanswerable | 主题相关，但缺少具体时间、数值或约定事实 | 20/40 |

## 数据来源与 gold

这是 **Codex 编写的虚构合成诊断集**。政策事实、gold answer 和问题在评测前由代码中的固定情景共同构建，没有调用被评测的 Gemma2 生成 gold，评测过程中也没有修订 gold。它不是独立人工标注，也不是自然企业文档/真实用户查询。

冻结 metadata 中 `no LLM gold` 只能说明未使用被评测模型生成参考答案，不能解释为没有语言模型参与作者工作；Codex 是数据编写者。为保持冻结结果身份，不重写该 metadata，来源解释在本说明中明确披露。

answerable 的 evidence span、PDF 页号和文件名明确指定；alignment 使用不变 V1 逻辑转换成 chunk IDs。unanswerable 只标记相关文档，没有人为创建相关 gold chunk。所有 180 positive spans 在 PDFium 实际提取内容中核对成功，90 份 PDF 的页数已核对；这些自动检查不是独立人工语义审阅。

## 隔离检查及其边界

`benchmark_integrity.json` 包括所有问题 normalized hash、源 PDF hash、计数与以下 dev/test 交叉检查：family、normalized question、将数字和表单 ID 抽象后的 template、标注 source span、SequenceMatcher≥0.9 或 token Jaccard≥0.8 的 near-duplicate。

当前没有触发项。但这不是完备泄漏证明：template 归一化主要处理数字与标识符，不会发现所有语义模板；source span overlap 仅针对 gold span，PDF 中公共管理说明与整体页结构有复用。code/answer 同源作者也可能引入作者偏差。每类 test 仅 20 正例。

标注粒度为 chunk：部分 hard-negative 的不同对象/资格事实放在同一页、同一 gold chunk 内，因此检索命中该 chunk 不能证明区分了页内的具体对象。生成实验仍需从这些事实中选择正确答案；跨 chunk 干扰主要来自其他家族、相邻标识符条目和历史版本。当前类别不能替代一个专门将各 cohort 拆成独立 chunk 的对抗检索集。

V2 主要增加 early ranking、版本选择和近似相关拒答诊断。若某方法 R@5/R@10 仍饱和，必须在报告中保留该限制，不能事后改 benchmark 使组件显得有效。

## 使用规则

本轮采用冻结 V1 算法和参数：candidate K=10、final K=10、context top5、RRF k=60。没有 query rewrite、HyDE、multi-query、Agent、GraphRAG 或训练。不能依据已经看过的 V2 test 修改门限、gold、问题或失败记录。

独立人工复核仍为 **PENDING_HUMAN_REVIEW**。V1 review template 的人工字段保持空白；如后续开展 V2 人工 gold 复核，应保留原冻结标签并单独记录勘误/新版本，不能覆盖本次正式结果。
