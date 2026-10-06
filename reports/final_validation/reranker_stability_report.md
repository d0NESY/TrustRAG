# Reranker 固定输入稳定性

30诊断题、两个固定候选来源、各5轮真实执行，共300查询/3000 passage score。最大score std=0、range=0，所有 Top1/完整排名和正式排名一致；对正式保存score最大差=0.0。

这是同机、同模型/代码/候选的条件性重复稳定，不保证不同 candidate pool 的输出等价。真实 batch probe 已发现两道固定 passage pair 翻转，具体 padding/量化根因尚未验证。原始每轮 query score/rank/top1/latency 见独立JSONL，分 passage 汇总见 reranker_stability.csv。
