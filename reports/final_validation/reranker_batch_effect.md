# Reranker Candidate Batch Composition Test

六道已观察到 shared-score drift 的诊断题，含两道版本 top1 reversal。固定 query、target 文本、competitor 文本及其 slot0/slot1；A/B/C 仅替换另外八个候选，size=10。另做既有 API 的 single-pair，所有条件各真实执行三次。

| id | set | score mean | score std | rank min | rank max | top1 rate | top5 rate | target-competitor margin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_parental_requests_version_conflict | A_dense | 0.918854 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.019064 |
| v2_parental_requests_version_conflict | B_hybrid | 0.927871 | 0.000000 | 2 | 2 | 0.000000 | 1.000000 | -0.011525 |
| v2_parental_requests_version_conflict | C_long_distractors | 0.924405 | 0.000000 | 2 | 2 | 0.000000 | 1.000000 | -0.003477 |
| v2_parental_requests_version_conflict | single_pair | 0.920827 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | None |
| v2_research_data_version_conflict | A_dense | 0.998279 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000153 |
| v2_research_data_version_conflict | B_hybrid | 0.998144 | 0.000000 | 2 | 2 | 0.000000 | 1.000000 | -0.000114 |
| v2_research_data_version_conflict | C_long_distractors | 0.998058 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000089 |
| v2_research_data_version_conflict | single_pair | 0.998177 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | None |
| v2_device_exit_semantic | A_dense | 0.931513 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.619833 |
| v2_device_exit_semantic | B_hybrid | 0.892754 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.508104 |
| v2_device_exit_semantic | C_long_distractors | 0.933314 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.682347 |
| v2_device_exit_semantic | single_pair | 0.938948 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | None |
| v2_device_exit_version_conflict | A_dense | 0.999885 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000700 |
| v2_device_exit_version_conflict | B_hybrid | 0.999882 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000644 |
| v2_device_exit_version_conflict | C_long_distractors | 0.999874 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000694 |
| v2_device_exit_version_conflict | single_pair | 0.999880 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | None |
| v2_visitor_facilities_version_conflict | A_dense | 0.999783 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000007 |
| v2_visitor_facilities_version_conflict | B_hybrid | 0.999810 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000031 |
| v2_visitor_facilities_version_conflict | C_long_distractors | 0.999778 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000019 |
| v2_visitor_facilities_version_conflict | single_pair | 0.999779 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | None |
| v2_incident_paging_version_conflict | A_dense | 0.999628 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000768 |
| v2_incident_paging_version_conflict | B_hybrid | 0.999621 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000740 |
| v2_incident_paging_version_conflict | C_long_distractors | 0.999603 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | 0.000708 |
| v2_incident_paging_version_conflict | single_pair | 0.999615 | 0.000000 | 1 | 1 | 1.000000 | 1.000000 | None |

不同集合的 rank 改变也可能来自竞争候选不同，不能全部归给 score 数值漂移。固定 target/competitor 的 margin 变号才直接说明同一对 passage 在其他候选变化时相对顺序改变；single-pair 的 rank=1 是结构性结果。完整 token/padding 长度、top1/top5/top10 与原始分数保存在独立 predictions。

固定 passage pair 相对次序变号的 case 数：2。动态 padding、ONNX 量化均为 mechanism hypothesis；这里没有改换权重/推理代码或做可归因单因素量化实验，不预设具体原因。

