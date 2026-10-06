# V2 Answerability score 分布

来自冻结 Hybrid+Reranker 的全部 queries。未选择新 feature 或阈值；AUC 为描述统计，20-bin overlap 依赖 binning。

| split | feature | answerable | N | P5 | P50 | P95 | AUC | Binned overlap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | top1 | True | 60 | 0.7385 | 0.9962 | 0.9996 | 0.9875 | 0.0333 |
| dev | top1 | False | 20 | 0.0000 | 0.0236 | 0.5532 | 0.9875 | 0.0333 |
| dev | top3_mean | True | 60 | 0.2918 | 0.3735 | 0.9973 | 0.9867 | 0.0333 |
| dev | top3_mean | False | 20 | 0.0000 | 0.0084 | 0.2011 | 0.9867 | 0.0333 |
| dev | margin | True | 60 | 0.0004 | 0.7591 | 0.9933 | 0.8067 | 0.3667 |
| dev | margin | False | 20 | 0.0000 | 0.0220 | 0.4893 | 0.8067 | 0.3667 |
| test | top1 | True | 120 | 0.5407 | 0.9938 | 0.9997 | 0.9631 | 0.1583 |
| test | top1 | False | 40 | 0.0001 | 0.0090 | 0.9139 | 0.9631 | 0.1583 |
| test | top3_mean | True | 120 | 0.2102 | 0.3424 | 0.9828 | 0.9415 | 0.2000 |
| test | top3_mean | False | 40 | 0.0001 | 0.0032 | 0.3314 | 0.9415 | 0.2000 |
| test | margin | True | 120 | 0.0002 | 0.8174 | 0.9961 | 0.8275 | 0.3667 |
| test | margin | False | 40 | 0.0000 | 0.0054 | 0.8538 | 0.8275 | 0.3667 |

正负 score 的实际范围、分位数和直方图已全部导出。重叠说明 topical relevance 与事实充足性不同；本轮不把任一 relevance feature 视为校准概率。完整 gate trade-off 见 FINAL_V2_REPORT.md 的 Q7/Q8。
