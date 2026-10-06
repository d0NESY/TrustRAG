"""Chinese reports grounded in saved V2 diagnostics, including negative findings."""

import json
from collections import Counter

from ragbase.evaluation.benchmark import read_jsonl
from scripts.v2.common import EXPERIMENTS, REPORTS


def write_md(name, content):
    (REPORTS / name).write_text(content, encoding="utf-8", newline="\n")


def find(rows, **conditions):
    return next(row for row in rows if all(row[key] == value for key, value in conditions.items()))


def render(retrieval, scores, gate, runs):
    from scripts.v2.analyze import table
    methods = {row["method"]: row for row in retrieval["overall"] if row["split"] == "test"}
    dense, dr, hybrid, hr = [methods[name] for name in ["dense", "dense_reranker", "hybrid", "hybrid_reranker"]]
    rescue = find(retrieval["rescue"], split="test", category="all")
    rrf = find(retrieval["rrf"], split="test", category="all")
    dense_rank = find(retrieval["reranker"], split="test", category="all", comparison="dense -> dense_reranker")
    hybrid_rank = find(retrieval["reranker"], split="test", category="all", comparison="hybrid -> hybrid_reranker")
    g0, g1 = [find(gate["overall"], split="test", condition=name) for name in ["G0_prompt_only", "G1_current_v1_gate"]]
    standalone = find(scores["standalone_gate"], split="test")
    top1 = find(scores["quantiles"], split="test", feature="top1", answerable=True)
    changed = gate["paired_changes"]["test"]
    added_context = gate["added_false_refusal_context"]["test"]
    cross_pool = find(retrieval["cross_pool_scores"], split="test")

    # Architecture selection is an explicit diagnostic conclusion, not a new
    # retrieval algorithm or a test-selected parameter. No config is recalibrated.
    hybrid_has_value = (hr["mrr"] > dr["mrr"] and hr["recall@1"] > dr["recall@1"]
                        and rescue["hybrid_rescue_vs_dense"] > 0)
    chosen = "Dense + BM25 + RRF + Reranker" if hybrid_has_value else "Dense + Reranker"
    chosen_key = "hybrid_reranker" if hybrid_has_value else "dense_reranker"
    chosen_row = methods[chosen_key]
    if hybrid_has_value:
        reason = "Hybrid 实际保留了 Dense 缺失的 gold，且重排后的 Recall@1 与 MRR 均高于 Dense + Reranker；这支持保留词法分支。"
    else:
        reason = "固定预算下，没有同时观察到可保留的 Dense candidate rescue 与重排后 Recall@1/MRR 净增益；优先选择组件更少的 Dense + Reranker。"
        if dr["mrr"] > hr["mrr"] and dr["recall@1"] > hr["recall@1"]:
            reason = "Dense + Reranker 的 test Recall@1 与 MRR 均更好，Hybrid 没有提供候选补回；额外词法索引与 RRF 的复杂度没有获得本轮质量收益支持。"
    gate_verdict = ("Current Gate 确实减少了 near-miss 的非拒答，但必须同时评估新增误拒答与 coverage 损失。"
                    if g1["answerability"]["false_answer_rate"] < g0["answerability"]["false_answer_rate"]
                    else "Current Gate 没有降低困难 near-miss 的 False Answer Rate。")
    # A final default enablement needs a positive, acceptable quality/coverage
    # trade-off. V2 round does not fit or pick a new threshold.
    gate_default_reason = "当前门限保持 experimental / optional，demo 默认关闭。本轮不基于 V2 test 调阈值。"

    reranker_verdict = ("两种候选源上的总体 MRR 均提高，重排仍是本轮可直接归因的有效排序组件。"
                       if dr["mrr"] > dense["mrr"] and hr["mrr"] > hybrid["mrr"]
                       else "并非两种候选源均获益，不能把重排器描述为无条件稳定提升。")
    high_negative = max((row for row in runs["test"]["hybrid_reranker"].values() if not row["answerable"]), key=lambda row: row["results"][0]["score"])
    low_positive = min((row for row in runs["test"]["hybrid_reranker"].values() if row["answerable"]), key=lambda row: row["results"][0]["score"])
    high_negative_output = next(row for row in read_jsonl(EXPERIMENTS / "test/G0_prompt_only/generation_predictions.jsonl") if row["id"] == high_negative["id"])
    category_gains = []
    for comparison in ["dense -> dense_reranker", "hybrid -> hybrid_reranker"]:
        categories = [row for row in retrieval["reranker"] if row["split"] == "test" and row["comparison"] == comparison and row["category"] != "all"]
        largest = sorted(categories, key=lambda row: -row["mean_rank_improvement"])[:3]
        category_gains.append(comparison + " 的平均首 gold 排名改善最多的类别为 " + "、".join(f"{row['category']}（delta={row['mean_rank_improvement']:.2f}）" for row in largest) + "。")

    report = f"""# TrustRAG V2：Hard Benchmark 与组件价值诊断

本轮使用真实本地模型运行，保留全部题目、原始预测和 judge 输出。最终推荐检索架构为 **{chosen}**；证据门限默认关闭。{reason}

V1 正式 test、预测、指标、报告、原实验配置和 21 个核心算法文件保持原字节 SHA-256。V2 分支为 `trust-rag-v2`，冻结实验代码提交记录在每组 `resolved_config.json`。V1 的既有结论与数字只在 `V1_FROZEN_BASELINE.md` 原样记录，本轮不重新跑 V1 test，也不覆盖 V1 报告。

## 1. 数据与受控条件

V2 为 **240 题：180 answerable + 60 near-miss unanswerable**，来自 30 个政策家族、90 份 PDF、180 页。dev 为 80 题（60/20），test 为 160 题（120/40）。按整个文档家族隔离，六种正例类别在 test 中各 20 题，near-miss 40 题。

本数据集由 Codex 在模型评测前编写政策情景、事实和问题，属于**合成诊断集**，不是自然企业日志或真实客户问答，也不是独立人工编写的 gold。没有调用被评测的 Gemma2 来产生或修改参考答案；dataset metadata 中的 `no LLM gold` 表述应限于这一点，不表示没有 Codex 参与数据编写。独立人工 gold 验证未完成。操作指南、历史版本和附件仍有共同管理性结构，因此零字符串重叠不能证明不存在一切语义模板关联。source span 检查只覆盖标注 gold，公共行政说明存在复用。

gold 以 chunk 为单位。部分 hard-negative 的多个 cohort 事实位于同页/同一 gold chunk；检索命中不代表模型已经正确区分页内事实，仍要看生成答案。其难度不能等同于将每个 cohort 独立分块的对抗检索集。细节见 `BENCHMARK_CARD.md`。

`benchmark_integrity.json` 记录 family、normalized question、数字/标识符抽象 template、gold span 和近重复检查；没有跨 split 的命中项。所有语料均进入同一无监督索引，问题和目标文档家族隔离；这是检索知识库共享，不是 dev/test 的监督标签共享。

冻结 V1：同一 page-normalized recursive chunks（2048 字符/128 overlap）、BGE base en v1.5、FlashRank MiniLM L12、RRF k=60、候选 K=10、最终 K=10、生成 context top5。每个分支最多 10，Hybrid RRF 输出前 10；原始并集最多 20 仅供覆盖诊断。模型校验和与原参数见 `experiments/v2/formal_v2_freeze.json`。

Gemma2:9b 的生成/固定 judge、temperature=0、seed=42、num_ctx=4096、输出上限与 V1 一致。当前门限仍为 top1 ≥ {standalone['threshold']:.17g}，没有在 V2 dev/test 重新校准。所有结果均为一次完整运行，支持同指纹 checkpoint 续跑；不对失败题做筛除。

独立人工审阅状态：**PENDING_HUMAN_REVIEW**。`reports/human_review_template.csv` 的人工字段为空。自动化检查、LLM judge 与 Codex 检查均不算独立人工审阅。

## 2. 检索总指标

ranking 仅统计 answerable；latency 统计全部题目，包含真实 query embedding、搜索/融合/重排，模型热身后测量，不使用查询 embedding 缓存。MRR 在保存深度 10 截断，nDCG@5 采用 binary chunk relevance。

"""
    headers = ["split", "method", "R@1", "R@3", "R@5", "R@10", "MRR", "nDCG@5", "Candidate R@10", "Mean ms", "P50 ms", "P95 ms"]
    report += table(headers, [[row[key] for key in ["split", "method", "recall@1", "recall@3", "recall@5", "recall@10", "mrr", "ndcg@5", "candidate_recall", "latency_mean_ms", "latency_p50_ms", "latency_p95_ms"]] for row in retrieval["overall"]])
    report += "\n\n## 3. Test query-type breakdown\n\n每类 20 道 answerable，不把类别小样本差异解释成普适或显著性结论。dev 和 test 完整明细见 `retrieval_by_category.csv`。\n\n"
    report += table(["category", "method", "R@1", "R@5", "MRR", "nDCG@5", "Candidate R@10"],
                    [[row[key] for key in ["category", "method", "recall@1", "recall@5", "mrr", "ndcg@5", "candidate_recall"]] for row in retrieval["by_category"] if row["split"] == "test"])
    winners = []
    for category in sorted({row["category"] for row in retrieval["by_category"]}):
        part = [row for row in retrieval["by_category"] if row["split"] == "test" and row["category"] == category]
        best = max(row["mrr"] for row in part)
        winners.append((category, ", ".join(row["method"] for row in part if row["mrr"] == best), best))
    report += "\n\n按本集 MRR 的类别最佳（含并列）：\n\n" + table(["category", "best methods", "MRR"], winners)
    report += f"""

## 4. Q1：原版到 TrustRAG 的 dev 增益如何归因？

原版复现实验的 dev Dense Recall@1=0.7667、MRR=0.8472，原版 Dense+Reranker Recall@1=0.8000、MRR=0.8389；V1 修改后的 dev Dense 与 Dense+Reranker 均为 1.0000。上述已有记录来自 `docs/original_baseline_results.md` 与 `experiments/*/dev/retrieval_metrics.json`，没有重测。

这不是仅替换 retrieval algorithm 的对照：原版整文档语义分块与页面元数据丢失，后续变为保留页信息的分块/对齐；Dense depth 从 5 变为 10，原版 FlashRank 最多输出 3，后续输出 10；索引、chunk identity 与 gold 对齐方式也不同。因此只能把大幅变化归为 **pipeline / chunking / depth / metadata 的联合变化**，无法给各因素分配单独因果份额，更不能把 0.8→1.0 归给新 BM25/RRF 或重排器。FlashRank 本身也是上游已有组件。

可作算法归因的是共享 chunks、模型、候选与最终预算的受控五组比较：V2 的 Dense→Dense+Reranker、Hybrid→Hybrid+Reranker 是对候选池不变的排序贡献；Dense→Hybrid 同时改变候选构成与 RRF 排序，需分开报告覆盖和排名。

## 5. Q2：Reranker 是否仍然有效？

{reranker_verdict}

Test Dense→Dense+Reranker：R@1 {dense['recall@1']:.4f}→{dr['recall@1']:.4f}，MRR {dense['mrr']:.4f}→{dr['mrr']:.4f}；首 gold 的 mean rank improvement={dense_rank['mean_rank_improvement']:.4f}、median={dense_rank['median_rank_improvement']:.4f}，improved={dense_rank['improved_percent']:.2f}%、degraded={dense_rank['degraded_percent']:.2f}%。

Test Hybrid→Hybrid+Reranker：R@1 {hybrid['recall@1']:.4f}→{hr['recall@1']:.4f}，MRR {hybrid['mrr']:.4f}→{hr['mrr']:.4f}；mean={hybrid_rank['mean_rank_improvement']:.4f}、median={hybrid_rank['median_rank_improvement']:.4f}，improved={hybrid_rank['improved_percent']:.2f}%、degraded={hybrid_rank['degraded_percent']:.2f}%。

完整类别分布见 `reranker_contribution.md`，逐题变化见 `reranker_rank_changes.csv`。候选池一致性已自动核验。Cross-Encoder 能改变现有候选的相对位置，不能找回未进入候选的 gold；降级案例完整保留。这里的“稳定”只指当前受控数据与两种候选源，不代表跨随机种子、领域或生成模型的稳定性。

{' '.join(category_gains)} 具体 improved/degraded 案例见 `diagnostic_examples.md`，按 question ID 固定排序取例，全部逐题记录仍保留。

## 6. Q3：BM25 在哪些类型存在 unique rescue？

Test K=10：BM25 rescue={rescue['Dense Miss / BM25 Hit']}，Dense rescue={rescue['BM25 Miss / Dense Hit']}，Both Hit={rescue['Both Hit']}，Both Miss={rescue['Both Miss']}；Hybrid 实际相对 Dense rescue={rescue['hybrid_rescue_vs_dense']}。按类别的全部计数见 `retrieval_rescue_analysis.md`。

"""
    bm25_categories = [f"{row['category']}={row['Dense Miss / BM25 Hit']}" for row in retrieval["rescue"] if row["split"] == "test" and row["category"] != "all" and row["Dense Miss / BM25 Hit"]]
    report += ("存在 BM25 candidate unique rescue 的类别：" + "，".join(bm25_categories) + "。\n" if bm25_categories else "本轮 test 没有 BM25 candidate unique rescue，不能凭 exact-term 的类别设计就宣称词法分支具有独有覆盖收益。词法排序上的局部收益需看 breakdown，与候选补回是两种证据。\n")
    report += f"""

Hybrid-only hit（两个分支都 miss 而 Hybrid hit）={rescue['hybrid_only_hit_vs_both_branches']}。RRF 只处理分支并集，该条件在此定义下结构性不可能，不能用它否认 Hybrid 相对 Dense 的 rescue。

## 7. Q4：Hybrid 是否改善 candidate recall？

Test Dense candidate R@10={dense['candidate_recall']:.4f}，Hybrid={hybrid['candidate_recall']:.4f}，差值={hybrid['candidate_recall'] - dense['candidate_recall']:+.4f}。原始 Dense/BM25 并集（最多 20，非正式 Hybrid 输出）的 recall={rescue['raw_union_candidate_recall']:.4f}。

Hybrid rescue vs Dense={rrf['hybrid_rescue_vs_dense']}、Hybrid loss vs Dense={rrf['hybrid_loss_vs_dense']}；并集中有 gold 但 RRF 前 10 丢弃全部 gold 的题目={rrf['rrf_dropped_union_gold']}。仅当真实固定预算 Hybrid 的覆盖率上升，才能宣称 candidate recall 改善；并集的更大预算不能作为同预算收益。

## 8. Q5：RRF 是否损害 early ranking？

Test Dense→Hybrid：R@1 {dense['recall@1']:.4f}→{hybrid['recall@1']:.4f}，MRR {dense['mrr']:.4f}→{hybrid['mrr']:.4f}，nDCG@5 {dense['ndcg@5']:.4f}→{hybrid['ndcg@5']:.4f}。首 gold rank improved={rrf['improved_percent']:.2f}%、degraded={rrf['degraded_percent']:.2f}%，mean delta={rrf['mean_rank_improvement']:.4f}。

"""
    if hybrid["candidate_recall"] > dense["candidate_recall"] and hybrid["mrr"] < dense["mrr"]:
        report += "本轮支持：Hybrid 改善候选覆盖，但 RRF 的 early ranking 损失抵消部分收益。\n"
    elif hybrid["mrr"] < dense["mrr"]:
        report += "本轮 RRF 的 MRR 低于 Dense；应结合候选损失和排名降级记录解释，不能只归因于候选多样性。\n"
    else:
        report += "本轮没有观察到 RRF 在总体 MRR 上的损失；仍需保留逐题降级与截断失败。\n"
    report += f"""

## 9. Q6：Hybrid+Reranker 的收益是否支持额外复杂度？

Test 对 Dense+Reranker：R@1 delta={hr['recall@1'] - dr['recall@1']:+.4f}、R@5 delta={hr['recall@5'] - dr['recall@5']:+.4f}、MRR delta={hr['mrr'] - dr['mrr']:+.4f}。mean latency {dr['latency_mean_ms']:.1f}→{hr['latency_mean_ms']:.1f} ms，差值={hr['latency_mean_ms'] - dr['latency_mean_ms']:+.1f} ms，P95 {dr['latency_p95_ms']:.1f}→{hr['latency_p95_ms']:.1f} ms。

{reason} 复杂度包括 BM25 索引维护、额外候选配置和 RRF 融合，而不是仅以某次毫秒差衡量。实测时间是同机、按方法顺序的一次运行，未做随机交错重复和误差估计；小延迟差不能宣称统计显著。V1 与 V2 查询、chunk 数量/长度和运行时负载不同，不能把跨版本 latency 差单独归因于算法。

补充诊断发现：两种重排候选池共享的 passage 在固定 ONNX 权重下也有保存分数差异，test 平均绝对差={cross_pool['shared_score_delta_abs_mean']:.6f}、最大={cross_pool['shared_score_delta_abs_max']:.6f}。Hybrid 重排比 Dense 重排降级的题目中，Hybrid top1 本来就在 Dense 候选池的题目={cross_pool['degraded_cases_with_top_already_in_dense_pool']}，不能把这些失败直接解释为 BM25 引入了新坏候选。FlashRank 按整个候选 batch 进行动态 padding/量化 ONNX 推理，batch 构成引起数值变化是待验证的机制假设；本轮只记录原预测中的 score drift，没有额外重跑或修复模型。详见 `reranker_shared_score_changes.csv` 与 `reranker_between_pools_rank_changes.csv`。

## 10. G0/G1：实际发布回答与单独 Gate

G0 保留原 grounding prompt 和引用 ID 核验，关闭分数 gate；G1 只开启原 V1 门限。两者共用 Hybrid+Reranker 已保存的检索结果。正例=实际发布非拒答；Precision/Recall/F1 是“是否应回答”的分类指标，不是答案内容正确率。

"""
    report += table(["split", "condition", "Precision", "Recall", "F1", "FAR", "FRR", "Coverage", "TP", "FP", "FN", "TN"],
                    [[row["split"], row["condition"], *[row["answerability"][key] for key in ["precision", "recall", "f1", "false_answer_rate", "false_refusal_rate"]], row["coverage"], *[row["answerability"][key] for key in ["tp", "fp", "fn", "tn"]]] for row in gate["overall"]])
    report += "\n\n单独 Gate 的允许/拒绝决策（尚未经过 LLM prompt 与引用检查）：\n\n"
    report += table(["split", "Precision", "Recall", "F1", "FAR", "FRR", "Coverage", "FP", "FN"],
                    [[row["split"], *[row[key] for key in ["precision", "recall", "f1", "false_answer_rate", "false_refusal_rate", "coverage", "fp", "fn"]]] for row in scores["standalone_gate"]])
    report += "\n\n生成质量（固定本地 LLM judge，非独立人工）：\n\n"
    report += table(["split", "condition", "Correctness", "Correctness N", "Groundedness", "Gold-source citation precision", "Judge failures", "Total P50 ms", "Total P95 ms"],
                    [[row["split"], row["condition"], row["answer_correctness"], row["answer_correctness_count"], row["groundedness"], row["citation_accuracy"], row["judge_failure_count"], row["total_latency_ms"]["p50_ms"], row["total_latency_ms"]["p95_ms"]] for row in gate["overall"]])
    report += "\n\n配对变化（G1 相对 G0）与门限直接影响分别列出：\n\n"
    report += table(["split", "G0 false answer→G1 refusal", "Direct gate prevented", "Added false refusal", "Direct gate added refusal", "Changed raw answer after pass"],
                    [[split, *[gate["paired_changes"][split][key] for key in ["prevented_false_answer", "score_gate_prevented_false_answer", "added_false_refusal", "score_gate_added_false_refusal", "raw_answer_changed_while_gate_allowed"]]] for split in ["dev", "test"]])
    report += f"""

judge 的无效 JSON 计入 failure count 并保留原输出，不填人工标签。Correctness 把 answerable 上拒答计为 0，其余 judge 失败按 V1 metric 定义排除并报告分母。gold-source citation precision 是来源相关性代理，不代表逐主张蕴含。online total 包含检索和生成，不包含离线 judge。

## 11. Q7：Current Gate 是否终于降低 False Answer？

{gate_verdict} Test FAR {g0['answerability']['false_answer_rate']:.4f}→{g1['answerability']['false_answer_rate']:.4f}，FRR {g0['answerability']['false_refusal_rate']:.4f}→{g1['answerability']['false_refusal_rate']:.4f}，coverage {g0['coverage']:.4f}→{g1['coverage']:.4f}。配对分析：G1 拒绝了 G0 的 false answer={changed['prevented_false_answer']}，G1 新增 false refusal={changed['added_false_refusal']}。其中由分数门限直接阻止的 false answer={changed['score_gate_prevented_false_answer']}，门限直接新增的 false refusal={changed['score_gate_added_false_refusal']}。逐题见 `gate_case_changes.csv`。

新增误拒答中，gold chunk 已在生成 context 内的题目={added_context['gold_source_in_context']}，完整标注 evidence span 在来源摘录中可按规范化字符串找到的题目={added_context['gold_evidence_exact_in_excerpts']}。后者只检查完整字符串存在，不能把未命中直接解释为没有可用事实，也不是独立人工正确性标签。分类误拒答率见 `gate_by_category.csv`。

门限放行后的两次 raw answer 不同的题目={changed['raw_answer_changed_while_gate_allowed']}；相同 prompt 的对应关系也保存在逐题 CSV。即使固定 seed，也不能先验假设两次运行完全相同。门限直接拒绝与放行后生成差异必须区分，所有结果照实计入。

{gate_default_reason} 如果 FAR 存在下降，也不能在没有明确可接受的 FRR/coverage 证据时自动恢复默认开启。无观察错误不等于真实风险为零；test near-miss 仅 40 题。

## 12. Q8：为什么 relevance score 不能直接当作 answerability confidence？

Test top1 AUC（高分视为 answerable）={top1['auc_positive_higher']:.4f}，20 等宽 bin 的 class-normalized overlap coefficient={top1['histogram_overlap_coefficient']:.4f}；当前门限单独 FAR={standalone['false_answer_rate']:.4f}、FRR={standalone['false_refusal_rate']:.4f}。两个分布的全部 quantile、histogram、逐题 top1/top3_mean/margin 与标签分别保存在 `answerability_score_quantiles.csv`、`answerability_score_histograms.csv`、`answerability_scores.csv` 和 `answerability_score_distributions.json`。

本轮 top1 具有较强整体区分信号，不能把它描述为“两类分布高度重叠”或“完全没有 answerability 信息”。但高分 near-miss `{high_negative['id']}` 的 top1={high_negative['results'][0]['score']:.6f}，低分可回答题 `{low_positive['id']}` 的 top1={low_positive['results'][0]['score']:.6f}，说明尾部仍有真实重叠，当前低门限并不能独立判断事实充足性。高 AUC、门限决策质量和端到端净收益是不同结论。

最高分 near-miss 的原问题：**{high_negative['question']}**；G0 输出：**{high_negative_output['answer']}**。在本集这个例子中，回答给出员工群体的车票规则，而问题需要材料未提供的客户身份。有引用且陈述受到来源支持，仍然可以答非所问；不能用相关性高分或 groundedness 代替所问事实存在性。

"""
    report += table(["feature", "answerable", "N", "P5", "P25", "P50", "P75", "P95", "AUC", "Binned overlap"],
                    [[row[key] for key in ["feature", "answerable", "count", "p5", "p25", "p50", "p75", "p95", "auc_positive_higher", "histogram_overlap_coefficient"]] for row in scores["quantiles"] if row["split"] == "test"])
    report += """

Cross-Encoder 学到的是 query/document relevance，不是“该材料是否包含问题指定事实”的概率。Near-miss 可以共享主题、对象与日期词，却缺失未来年份、具体金额或约定条件；因此可能产生高相关分但仍不可回答。反过来，语义改写、精确标识符或有效版本选择可能分数偏低，但 gold 事实确实存在。top3_mean 和 margin 也只是排序形态，AUC 与量化重叠是诊断，不是新置信度模型或重新校准结果。

若同一 feature 的正/负分布存在实际范围重叠，本集不支持把它作为单独 answerability confidence。即使某个特征的 AUC 较高，也不能把未经概率校准的 score 当作可靠概率，或在已经看过 test 后选择新特征/阈值。重排器解决相关性排序；prompt 与引用核验负责当前发布策略的部分防护，两者仍可能遗漏具体事实缺失或版本错误。

## 13. 最终架构与限制

完整选择、替代方案、收益、latency、失败模式见 `architecture_decision.md`。V2 只运行五组检索与 Hybrid+Reranker 上 G0/G1 的端到端门限对照；没有宣称所选 Dense+Reranker 在 V2 上已经完成新的生成质量实验。检索架构选择与已测 gate 结果必须分开看。

本轮没有增加 query rewrite、HyDE、multi-query、Agent、GraphRAG、训练或图结构。没有因结果不利而改 gold、删题或调 test。该诊断集在 early ranking、版本、hard negatives 和拒答上可暴露失败，但候选 R@10 或 R@5 若仍接近饱和，需明确承认剩余难度限制；未来更自然独立语料属于另一次事先冻结的研究，不修改本轮。

复现命令见 `REPRODUCE.md`。`artifact_verification.json` 记录所有 V2 实验文件 SHA-256、完整预测计数、逐组 metric 重新计算与 V1 hash 检查结果。额外字节快照保留 262 个 V1 文件（包括原保护清单、核心代码和既有文档）的精确原字节，供独立新 clone 处理 Git 的换行转换；原工作目录不允许恢复写入。新增 V2 文件通过 `.gitattributes` 保留字节。人工复核仍待完成。
"""
    if (REPORTS / "demo_ui_results.json").exists():
        report += "\n真实浏览器 smoke 检查已完成：默认 Dense + 重排、门限关闭、带引用回答、prompt 拒答、实际 PDF 上传、文件名/页码展示和清空聊天记录。截图与原始 UI 文本保存在 `demo_screenshots/` 和 `demo_ui_results.json`；当前 V2 服务使用 http://127.0.0.1:8502。\n"
    write_md("FINAL_V2_REPORT.md", report)

    decision = f"""# V2 架构决策

**Chosen architecture：{chosen} + 原 grounding prompt + 引用核验。Current Gate 默认关闭，仅保留 experimental / optional。**

{reason}

## Measured benefit

Test 120 道 answerable：所选检索 R@1={chosen_row['recall@1']:.4f}、R@5={chosen_row['recall@5']:.4f}、MRR={chosen_row['mrr']:.4f}、nDCG@5={chosen_row['ndcg@5']:.4f}、candidate R@10={chosen_row['candidate_recall']:.4f}。

Dense→Dense+Reranker 的 MRR delta={dr['mrr'] - dense['mrr']:+.4f}，Hybrid→Hybrid+Reranker delta={hr['mrr'] - hybrid['mrr']:+.4f}。Hybrid+Reranker 相对 Dense+Reranker R@1 delta={hr['recall@1'] - dr['recall@1']:+.4f}、MRR delta={hr['mrr'] - dr['mrr']:+.4f}。Test BM25 candidate rescue={rescue['Dense Miss / BM25 Hit']}，实际 Hybrid rescue={rescue['hybrid_rescue_vs_dense']}。

## Latency cost

所选检索 mean={chosen_row['latency_mean_ms']:.1f} ms、P50={chosen_row['latency_p50_ms']:.1f} ms、P95={chosen_row['latency_p95_ms']:.1f} ms。Dense+Reranker mean={dr['latency_mean_ms']:.1f} ms，Hybrid+Reranker mean={hr['latency_mean_ms']:.1f} ms。Dense 重排相对不重排 mean 增加 {dr['latency_mean_ms'] - dense['latency_mean_ms']:.1f} ms。

这是一次 warm-run 实测，包含所有 test queries；没有重复测量置信区间，不能把小差异当成确定性能优势。BM25/RRF 的工程成本还包括索引和融合参数维护。

## Rejected / non-default alternatives

- Dense：省去重排计算，但本集早期排序指标见正式对照；是否能接受质量损失取决于应用 SLA，当前优先保留重排。
- BM25：Test R@1={methods['bm25']['recall@1']:.4f}、MRR={methods['bm25']['mrr']:.4f}、mean={methods['bm25']['latency_mean_ms']:.3f} ms；计算成本很低，但排序质量和候选覆盖低于所选方案。可作为延迟优先的独立对照，本次以检索质量为优先选择重排。
- Hybrid without reranker：RRF 同时涉及候选扩展和早期排序，不能仅按候选多样性选型。
- {('Dense + Reranker' if hybrid_has_value else 'Hybrid + Reranker')}：{('更简单，但本轮遗漏了可由词法分支实际保留的候选与重排后指标收益。' if hybrid_has_value else '本轮增益不足以支持把 BM25 + RRF 作为默认必选组件；保留实验对照配置。')}
- Current Gate：Test FAR {g0['answerability']['false_answer_rate']:.4f}→{g1['answerability']['false_answer_rate']:.4f}，FRR {g0['answerability']['false_refusal_rate']:.4f}→{g1['answerability']['false_refusal_rate']:.4f}，coverage {g0['coverage']:.4f}→{g1['coverage']:.4f}；默认关闭，不把 relevance threshold 宣传为已证明的置信度防护。

## Failure modes and practical limits

候选缺失无法通过 reranker 修复；版本冲突、相邻标识符、cohort/数值混淆仍需逐题检查。RRF 前 10 丢失并集 gold={rrf['rrf_dropped_union_gold']}；重排降级比例 Dense={dense_rank['degraded_percent']:.2f}%、Hybrid={hybrid_rank['degraded_percent']:.2f}%。Current Gate 新增误拒答={changed['added_false_refusal']}，阻止 false answer={changed['prevented_false_answer']}。

分数只代表相关性；近似相关不等于存在所需事实。prompt/citation 核验并非完备事实校验，LLM judge 有误差。V2 合成数据不等于真实部署分布；每类仅 20 道 test，独立人工审阅仍为 PENDING_HUMAN_REVIEW。

G0/G1 生成实验只覆盖 Hybrid+Reranker。选择 Dense+Reranker 时，不据此冒称其 V2 端到端正确率、FAR 和延迟已测；后续若要验证部署质量，需要另行预先冻结生成对照，不能重新调整本次 gold/test。

## Decision rationale

架构选择是对冻结实验的工程取舍，不是 test 调参。保留原模型、分块、candidate K=10、final K=10 和重排参数；不新增功能。默认 demo 的 gate-off 配置与 V1 实验配置分开，V1 原配置保持冻结。所有逐题失败保存在 experiments/v2 和对应诊断 CSV。
"""
    write_md("architecture_decision.md", decision)
    (REPORTS / "architecture_decision.json").write_text(json.dumps({"chosen_retrieval": chosen_key, "chosen_architecture": chosen,
                                                                   "gate_default": False, "human_review": "PENDING_HUMAN_REVIEW",
                                                                   "decision_basis": reason}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gate_rows = {split: {condition: read_jsonl(EXPERIMENTS / split / condition / "generation_predictions.jsonl") for condition in ["G0_prompt_only", "G1_current_v1_gate"]} for split in ["dev", "test"]}
    refusal_counts = {split: {condition: dict(Counter(row["refusal_reason"] or "published" for row in rows)) for condition, rows in conditions.items()} for split, conditions in gate_rows.items()}
    (REPORTS / "refusal_reason_counts.json").write_text(json.dumps(refusal_counts, indent=2) + "\n", encoding="utf-8")
    examples = "# V2 逐题诊断示例\n\n全部失败与成功保存在原始 predictions/CSV。以下按固定排序取每种条件最前面的最多三例，仅用于阅读，不改变指标或 gold。\n\n"
    for base, final in [("dense", "dense_reranker"), ("hybrid", "hybrid_reranker")]:
        from scripts.v2.diagnostics import first_gold_rank
        for direction in ["improved", "degraded"]:
            candidates = []
            for identity, row in runs["test"][base].items():
                if not row["answerable"]:
                    continue
                before = first_gold_rank(row["ranked_chunk_ids"], row["gold_chunk_ids"])
                after = first_gold_rank(runs["test"][final][identity]["ranked_chunk_ids"], row["gold_chunk_ids"])
                if (before > after if direction == "improved" else before < after):
                    candidates.append((identity, row["category"], row["question"], before, after))
            examples += f"## {base} → {final}：{direction}\n\n"
            examples += table(["id", "category", "question", "before", "after"], sorted(candidates)[:3]) + "\n\n" if candidates else "没有符合条件的 test case。\n\n"
    for label, condition in [("G1 新增误拒答", lambda a, b: a["answerable"] and not a["abstained"] and b["abstained"]),
                             ("G0 near-miss false answer", lambda a, b: not a["answerable"] and not a["abstained"]),
                             ("G1 near-miss false answer", lambda a, b: not b["answerable"] and not b["abstained"])]:
        g1_by_id = {row["id"]: row for row in gate_rows["test"]["G1_current_v1_gate"]}
        candidates = [row for row in gate_rows["test"]["G0_prompt_only"] if condition(row, g1_by_id[row["id"]])]
        examples += f"## {label}\n\n"
        for row in sorted(candidates, key=lambda row: row["id"])[:3]:
            other = g1_by_id[row["id"]]
            examples += f"- `{row['id']}`，top1={other['evidence_features']['top1']:.6f}。Question: {row['question']}\n\n  Gold: {row['gold_answer']}\n\n  G0: {row['answer']}\n\n  G1: {other['answer']}\n\n"
        if not candidates:
            examples += "没有符合条件的 test case。\n\n"
    examples += "## Score 尾部反例\n\n"
    generation_by_id = {row["id"]: row for row in gate_rows["test"]["G0_prompt_only"]}
    for row in [high_negative, low_positive]:
        outcome = generation_by_id[row["id"]]
        examples += f"- `{row['id']}`，answerable={row['answerable']}，top1={row['results'][0]['score']:.6f}。Question: {row['question']}\n\n  Gold: {outcome['gold_answer']}\n\n  G0: {outcome['answer']}\n\n"
    write_md("diagnostic_examples.md", examples)

    dist_report = "# V2 Answerability score 分布\n\n来自冻结 Hybrid+Reranker 的全部 queries。未选择新 feature 或阈值；AUC 为描述统计，20-bin overlap 依赖 binning。\n\n"
    dist_report += table(["split", "feature", "answerable", "N", "P5", "P50", "P95", "AUC", "Binned overlap"],
                         [[row[key] for key in ["split", "feature", "answerable", "count", "p5", "p50", "p95", "auc_positive_higher", "histogram_overlap_coefficient"]] for row in scores["quantiles"]])
    dist_report += "\n\n正负 score 的实际范围、分位数和直方图已全部导出。重叠说明 topical relevance 与事实充足性不同；本轮不把任一 relevance feature 视为校准概率。完整 gate trade-off 见 FINAL_V2_REPORT.md 的 Q7/Q8。\n"
    write_md("answerability_score_distributions.md", dist_report)
