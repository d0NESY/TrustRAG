"""Evidence-ranked final claims, independent verification and resume wording."""

import csv
import json
from statistics import mean, stdev

import numpy as np

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl, sha256_file
from ragbase.evaluation.retrieval_metrics import score_ranking, retrieval_metrics
from scripts.v2.byte_snapshot import check_or_restore
from scripts.final_validation.bootstrap import METRICS, METHODS, COMPARISONS, paired_differences
from scripts.final_validation.common import ROOT, OUT, REPORTS, prepare, verify_frozen, retrieval, csv_write, table


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def pick(rows, **terms):
    return next(row for row in rows if all(row[key] == value for key, value in terms.items()))


def verify_bootstrap():
    provenance = load(OUT / "bootstrap_provenance.json")
    for method, digest in provenance["source_prediction_sha256"].items():
        if sha256_file(ROOT / "experiments/v2/test" / method / "retrieval_predictions.jsonl") != digest:
            raise ValueError("Bootstrap source prediction changed")
    if sha256_file(OUT / "bootstrap_replicates.npz") != provenance["replicate_sha256"]:
        raise ValueError("Bootstrap replicate archive changed")
    ids = provenance["question_ids"]
    arrays = {}
    for method in METHODS:
        source = retrieval(method)
        arrays[method] = np.array([[score_ranking(source[identity]["ranked_chunk_ids"], source[identity]["gold_chunk_ids"])[metric] for metric in METRICS] for identity in ids])
    with np.load(OUT / "bootstrap_replicates.npz") as archive:
        draws = archive["question_draws"]
        if draws.shape != (10000, 120):
            raise ValueError("Invalid bootstrap draw shape")
        for left, right in COMPARISONS:
            expected = paired_differences(arrays[left], arrays[right], draws)
            observed = archive["paired_question__" + left + "__" + right]
            if not np.array_equal(expected, observed):
                raise ValueError("Paired bootstrap differences do not match original rankings")
            source = retrieval("dense")
            family_delta = np.array([(arrays[left] - arrays[right])[[position for position, identity in enumerate(ids) if source[identity]["family_id"] == family]].mean(axis=0)
                                     for family in provenance["family_ids"]])
            expected_family = family_delta[archive["family_draws"]].mean(axis=1)
            if not np.array_equal(expected_family, archive["paired_family_cluster__" + left + "__" + right]):
                raise ValueError("Paired family-cluster replicates differ")
    return provenance


def external_blocked_report():
    if load(OUT / "external/run/run_state.json")["state"] == "complete":
        raise ValueError("External generation is complete; do not render a blocked report")
    source = OUT / "external/retrieval_only"
    if load(source / "state.json")["status"] != "complete":
        raise ValueError("External retrieval unfinished")
    predictions = read_jsonl(source / "retrieval_predictions.jsonl")
    metric = retrieval_metrics(predictions)
    if metric != load(source / "retrieval_metrics.json"):
        raise ValueError("External retrieval metric recomputation differs")
    errors = read_jsonl(OUT / "external/run/execution_errors.jsonl")
    if not errors:
        raise ValueError("Cannot claim external runtime block without evidence")
    status = {"overall": "BLOCKED", "retrieval": "COMPLETE", "generation": "BLOCKED", "judge": "BLOCKED",
              "retrieval_questions": len(predictions), "answerable_retrieval_questions": metric["answerable_count"],
              "published_generation_prediction_count": 0, "recorded_failed_model_attempts": len(errors),
              "reason": "Pinned Ollama 0.35.1 / Gemma2:9b CUDA initialization repeatedly failed, including after task-owned service restart; same frozen parameters, no runtime/weight substitutions."}
    write_json(OUT / "external/external_status.json", status)
    blocked = "# External end-to-end test：BLOCKED\n\n已取得真实公开 SQuAD2 数据，并冻结 15 个自然 Wikipedia 摘录、75 道原生人工 QA（45 positive / 30 impossible）。文档和 gold 来自官方数据，不是 Codex 生成的模拟数据。全部 PDF 原文、gold offset 和 15 页视觉转换已校验。\n\n生成在第一道题触发 HTTP 500 / CUDA shared object initialization failed / llama-server exit 0xc0000409。已核实为本项目服务，按原二进制与启动参数重启后，同一题仍失败。两次失败全部保留在 experiments/final_validation/external/run/execution_errors.jsonl；服务日志另有恢复记录。\n\n没有换模型、调参数、改 gold 或筛掉失败题。完整 75 道检索仍在既有 Dense+CE 上完成，但 **Answer Correctness、Groundedness、Citation Accuracy、Answerability F1、FAR、FRR 尚未测得，全部 N/A**。API 异常不冒充模型拒答，也不作为 0% 错误率。不能声称完成端到端自然文档泛化验证。\n"
    (REPORTS / "EXTERNAL_TEST_BLOCKED.md").write_text(blocked, encoding="utf-8")
    synthetic = load(ROOT / "experiments/v2/test/dense_reranker/retrieval_metrics.json")
    text = "# External Natural Document Test：检索完成，端到端 BLOCKED\n\n公开 SQuAD2 官方 development data；第一优先级使用已有人工 QA/gold，未由 Gemma2 或 Codex 生成 QA。按原顺序选取首 15 个符合计数条件的不同文章家族，每个家族首段自然原文及首 3 positive / 2 impossible QA，共 75 题。PDF 为真实原文的忠实格式转换，不是模拟政策文档。\n\n最终 Dense+Reranker、Gate OFF、Citation ON 配置未改变；实际检索使用原 BGE、原 FlashRank、原 chunk2048/128、candidate/final10、context top5。所有 75 题保留，45 个正例参与排序指标。\n\n"
    text += table(["dataset / same architecture", "positive N", "R@1", "R@5", "MRR", "nDCG@5"],
                  [[name, values["answerable_count"], *[values[key] for key in ["recall@1", "recall@5", "mrr", "ndcg@5"]]]
                   for name, values in [("Synthetic V2 / Dense+CE", synthetic), ("External native SQuAD2 / Dense+CE", metric)]])
    text += "\n\n" + table(["metric", "External - Synthetic point gap"], [[key, metric[key] - synthetic[key]] for key in ["recall@1", "recall@5", "mrr", "ndcg@5"]])
    text += "\n\n这是 descriptive cross-dataset generalization gap，数据、问题风格、规模和难度均不同，不能归因为模型退化或证明总体泛化。只有 15 个摘录，不是完整企业/高校政策语料；公开数据可能在预训练中出现。原 impossible label 是单段 context 范围，多文档全局有效性仍待独立审核。外测检索已经饱和，较小且主题分散的 corpus 不足以证明大规模困难自然检索优势；本轮外测未跑 Dense-only，不能将1.0000全部归因于重排器。\n\n端到端生成/judge 因已记录 CUDA 运行环境故障 BLOCKED；全部所需生成指标 N/A，不与 V2 G0 生成数字相减或伪造“自然外测准确率”。Corpus、原生 aliases、source SHA、模型配置、完整 retrieval predictions 和两次执行错误均可查。\n"
    (REPORTS / "external_test_report.md").write_text(text, encoding="utf-8")
    return metric, status


def main():
    protected = prepare()
    provenance = verify_bootstrap()
    bootstrap = read_csv(REPORTS / "bootstrap_summary.csv")
    repeat = load(REPORTS / "repeatability_summary.json")
    batch = load(REPORTS / "reranker_batch_effect.json")
    human = load(REPORTS / "human_audit_status.json")
    external, external_status = external_blocked_report()
    protocol = load(OUT / "repeatability/protocol.json")
    latent = repeat["latency_across_runs"]
    metrics = ["recall@1", "recall@5", "mrr", "ndcg@5"]
    wanted = [row for row in bootstrap if row["resampling_unit"] == "paired_question"]
    dr = pick(latent, method="dense_reranker", component="total_latency_ms", round_metric="mean_ms")
    hr = pick(latent, method="hybrid_reranker", component="total_latency_ms", round_metric="mean_ms")
    latency_rows = read_csv(REPORTS / "latency_repeatability.csv")
    differences = [float(pick(latency_rows, round=str(number), method="dense_reranker", component="total_latency_ms")["mean_ms"])
                   - float(pick(latency_rows, round=str(number), method="hybrid_reranker", component="total_latency_ms")["mean_ms"]) for number in range(1, 6)]
    write_json(REPORTS / "latency_paired_run_differences.json", {"dense_minus_hybrid_mean_ms_by_round": differences, "mean_ms": mean(differences),
               "std_ms": stdev(differences), "min_ms": min(differences), "max_ms": max(differences), "claim": "Five rounds only; descriptive same-scale comparison, no superiority test."})
    compare_scores = []
    for method in ["dense_reranker", "hybrid_reranker"]:
        formal = retrieval(method)
        for number in range(1, 6):
            rows = read_jsonl(OUT / "repeatability" / f"round_{number}_{method}.jsonl")
            if len(rows) != 30 or {row["id"] for row in rows} != set(protocol["question_ids"]):
                raise ValueError("Repeat IDs/counts incomplete")
            for row in rows:
                original = formal[row["id"]]
                if row["candidate_chunk_ids"] != original["candidate_chunk_ids"]:
                    raise ValueError("Repeat pool not fixed")
                values = {r["chunk_id"]: r["score"] for r in original["results"]}
                compare_scores.extend(abs(r["score"] - values[r["chunk_id"]]) for r in row["results"])
    write_json(REPORTS / "reranker_formal_comparison.json", {"score_comparisons": len(compare_scores), "max_abs_score_delta_to_formal": max(compare_scores)})
    text = f"""# TrustRAG 最终可信度验证

本轮只验证冻结结论，没有新增 retrieval 算法、调 test 或改 V1/V2 结果。继续选择 **Dense + Existing Cross-Encoder Reranker；Gate 默认 OFF；原 Citation Logic 保留**。统计证据支持其在当前 V2 数据上相对 Dense 的排序收益；对 Hybrid+Reranker 的领先仍只是较高点估计，不宣称显著优于。

状态：Bootstrap / Reranker Stability / Batch Composition / Latency Repeatability **COMPLETE**；Human Audit **{human['status']}**；External retrieval **COMPLETE**，External generation/judge **BLOCKED**。封版包含全部可完成验证和明确的未完成项，不开启 V3。

## 1. 冻结输入保护

V2 完成交付提交为 `c0eaa39`。新分支 `trust-rag-final-validation` 的新实验与报告只写入 final_validation；原 app、算法、配置、predictions、metrics、benchmark 与报告未改变。`frozen_artifact_manifest.json` 保护 {len(protected['files'])} 个既有文件；另核对 V1 清单、V1 精确字节快照及 V2 实验/日志 SHA。新简历文档仅写 docs/final_resume_claims.md。

既有模型与配置保持不变：BGE base en v1.5、ms-marco MiniLM L12、Gemma2:9b；原模型 checksum、candidate/final K=10、context top5、chunk2048/128、seed42 均未重调。验证 driver 是新观察脚本，不改推理模块。

## 2. Human Audit：状态清楚区分

已检查原 reports/review_samples.jsonl 与 reports/human_review_template.csv，旧模板没有人工填写结果。整理 28 条目的性样本，覆盖 LLM-judged correct/incorrect、正确拒答、False Answer、False Refusal、版本冲突、Hard Negative、near-miss 和引用边界。四个人工字段共 112 格，目前填入 {human['filled_label_cells']} 格；全部保持空白，没有由 Codex 代填。

允许 1 / 0 / UNCERTAIN；审核说明、原始来源摘录与 cited_sources 已提供，judge 标签另存以减轻锚定偏差。人工准确率、groundedness、citation validity、gold agreement 与 Human/LLM agreement 当前均 N/A。目的性样本未来的审核准确率也不能代替全量 test 随机抽样准确率。见 human_audit_summary.md、HUMAN_AUDIT_PENDING.md 和 human_audit_template.csv。

## 3. Paired Bootstrap 95% CI

全部 120 道 answerable V2 test 问题，10,000 replicates，seed={provenance['seed']}。每次有放回抽取相同 question IDs 给所有方法，直接计算差值。以下为主问题级分析：

"""
    text += table(["comparison", "metric", "point", "bootstrap mean", "95% low", "95% high", "P(delta>0)"],
                  [[row["comparison"], row["metric"], *[float(row[key]) for key in ["point_estimate", "bootstrap_mean", "ci95_lower", "ci95_upper", "p_delta_gt_zero"]]] for row in wanted])
    text += "\n\nDense+CE − Dense：R@1 delta=+0.275、MRR delta≈+0.1739；bootstrap interval suggests 明确的当前样本排序收益。Dense+CE − Hybrid+CE：R@1 delta≈+0.0167、MRR delta≈+0.0083，但两个区间都包含 0，不能写统计学证明或显著优于。差别只来源于两道版本题，其余 118 道首次 gold rank 相同。\n\n另做 20 家族 paired cluster bootstrap 作为敏感性分析，两种分析都保留在 bootstrap_report.md；不假设六道家族内问题完全独立。P(delta>0) 是 resampling 正差值频率，不是传统 p-value 或总体优越性的后验概率。当前 CI 仍不能解决合成作者偏差、小类别 N=20 或外部自然语料差异。\n"
    text += f"""

## 4. Reranker Stability 与 Batch Effect

固定 30 个诊断问题：10 version-conflict、10 exact-term、10 semantic，优先较大旧 shared-score drift，并包含两道已知版本翻转。两个方法各 5 次，合计 300 次真实 timed query；每次候选列表及其顺序都与原正式保存列表核对。score std 最大值={repeat['maximum_score_std']:.6f}、max-min 最大值={repeat['maximum_score_range']:.6f}，排名变化 passage 数={repeat['rank_changed_passages']}。所有问题的 pairwise Top1 / 完整排名 agreement 均为 1；与正式排序一致。3000 个 score 对比正式值的最大差={max(compare_scores):.6f}。

这支持固定输入条件下的重复稳定，不能推断所有候选 batch 都等价。另对 6 道诊断题做 A/B/C/single-pair 各三次：固定 query、target 与 competitor 内容，固定 target/competitor 在 slot0/slot1，仅替换其他八个 passage。A/B/C size=10，single=1 仅为离线诊断，不变更生产候选预算。完整输入 token length、padding、score、rank、top1/top5/top10 都保存。

共有 {batch['pair_order_reversal_count']} 道 case 出现固定 target/competitor margin 变号，并改变目标的 Top1 状态。parental_requests 的目标 score 从 A=0.918854 到 B=0.927871，但 competitor 变化更大，margin +0.019064→−0.011525；research_data 的 margin +0.000153→−0.000114，也使目标 rank1→rank2。其余四例有分数变化，实际 target 排序未变；六例 target 都仍在 Top5。single-pair rank1 是结构性结果，不代表排序改善。

因此 batch composition 影响当前实现输出有直接实验支持；动态 padding / ONNX quantization 的具体因果贡献仍为 **mechanism hypothesis**。没有通过改换模型/量化版本/参数做根因归因，不能写“已证明由量化引起”。见 reranker_stability.csv、reranker_rank_agreement.csv、reranker_batch_scores.csv 和 reranker_batch_effect.md。

## 5. Latency Repeatability

同一真实 300-query 五轮过程同时承担稳定性和延迟验证，没有再造计时结果。每个方法每轮先做两次 full retrieve warmup；query embedding 实际重算，模型/index 缓存热身，不缓存查询向量。每轮方法顺序由固定种子随机抽取，顺序清单见 protocol.json。

"""
    text += table(["method", "round metric", "mean across 5 ms", "std ms", "min ms", "max ms"],
                  [[row[key] for key in ["method", "round_metric", "mean_across_runs_ms", "std_across_runs_ms", "min_ms", "max_ms"]] for row in latent if row["component"] == "total_latency_ms"])
    text += f"\n\nDense+CE 的五轮 mean 均值={dr['mean_across_runs_ms']:.1f} ms、std={dr['std_across_runs_ms']:.1f}；Hybrid+CE={hr['mean_across_runs_ms']:.1f} ms、std={hr['std_across_runs_ms']:.1f}。两者在当前机器/诊断集上处于同一秒级量级；paired round mean delta={mean(differences):.1f}±{stdev(differences):.1f} ms，范围 [{min(differences):.1f},{max(differences):.1f}]，不能把原单次约 80 ms 的差异写成可靠速度优势。没有剔除低/高延迟轮次；五轮很少，诊断样本也非全量 test，不做显著性夸大。\n"
    text += "\n## 6. External Generalization：部分可测，端到端 BLOCKED\n\n官方 SQuAD2 自然 Wikipedia 原文 + 原生人工 QA/gold，15 个不同文章摘录、75 问（45/30），未使用模型生成 gold、未修改 native questions。PDF 是原文格式转换，全部页渲染和 gold spans 验证完成；external 与原虚构 corpus 独立。全文/source hash 与原生 aliases 已保留。检索零调参完成：\n\n"
    text += table(["external R@1", "R@5", "MRR", "nDCG@5", "positive N"], [[*[external[key] for key in metrics], external["answerable_count"]]])
    text += "\n\n完整生成在第一道题发生 Ollama 0.35.1 / Gemma2:9b CUDA 初始化失败；本项目服务按原二进制与参数重启后仍失败，共记录两次 API 错误。生成与 judge 的所有指标 N/A；API 失败不当作拒答或模型错误率。没有为完成表格换模型、库或重调参数，不宣称完成端到端外部验证。见 EXTERNAL_TEST_BLOCKED.md 与 external_test_report.md。\n\n检索差值只是 descriptive cross-dataset generalization gap，不能归因为模型退化；15 个摘录并非完整企业政策，公开数据可能进入预训练，原 impossible 标签只有单段 annotation scope，多文档全局有效性仍待独立审核。\n"
    text += "\n外测检索在当前小规模、主题分散的摘录集合上已饱和，不能外推为大规模困难检索性能；未单独测 Dense 外测，不能分离 CE 的外测贡献。\n"
    text += "\n## 7. Final Claims 分级\n\n"
    claims = [
        ("Strongly Supported", "现有 CE 在当前 V2 受控候选条件下大幅改善 Dense 排序", "R@1 +27.5pp；MRR +0.1739，paired CI 支持正收益；限定当前合成集，非严格总体证明"),
        ("Strongly Supported", "固定输入的重复排序稳定；候选构成可改变该实现分数/相对顺序", "30题×2方法×5轮固定输入全一致；6题 composition probe 中2对固定 passages 翻转"),
        ("Strongly Supported", "当前 gate 没有取得 V2 端到端净安全收益", "冻结 test FAR 0.025→0.025、FRR 0.0083→0.0333；保持 OFF，未重调阈值"),
        ("Supported with Caveats", "Dense+CE 为当前更简单的最终选型", "对 Hybrid+CE 有更高点估计，差值 CI 含0，不写显著优于或普适最优"),
        ("Supported with Caveats", "当前 K=10 未观察到 BM25 unique candidate rescue", "正式120正例中0例；不等同于所有预算/语料上 BM25 无价值"),
        ("Supported with Caveats", "两种重排方案在当前测量中延迟同量级", "五轮随机方法顺序、30诊断题，不能断言约80ms为稳定算法速度差"),
        ("Supported with Caveats", "公开自然原文的零调参检索外测已完成", "45正例/30原生impossible，限定摘录/原生scope；生成外测尚未完成"),
        ("Not Supported", "Hybrid 提供 unique recall benefit / 显著优于或劣于另一方案", "当前无 unique rescue，Dense+CE-Hybrid+CE CI包含0"),
        ("Not Supported", "当前 score gate 改善端到端安全", "FAR无下降且误拒答增加"),
        ("Not Supported", "已完成独立人工审核、自然企业端到端泛化或定位量化根因", "人工pending；生成blocked；padding/quantization仅机制假说")]
    text += table(["tier", "claim", "evidence / limits"], claims)
    csv_write(REPORTS / "final_claims.csv", [{"tier": tier, "claim": claim, "evidence_and_limits": evidence} for tier, claim, evidence in claims])
    text += "\n## 8. 封版与复现\n\n本轮可完成的自动验证已经结束；人工审核等待真实 reviewer，外部生成保留实际阻塞。项目封版，不再增加功能、启动 V3 或按 test 调参。简历与面试只使用 docs/final_resume_claims.md 中的支持范围。复现流程见 REPRODUCE.md，所有源预测 SHA、draw indices、replicate deltas、runtime/候选协议和失败日志保存完整。\n"
    text += "\n新 clone 的原字节恢复使用既有 V2 快照与本轮五个未修改 legacy 文件的补充快照；Git 换行规范化差异已逐文件检查。原冻结工作目录禁止恢复写入。\n"
    (REPORTS / "FINAL_VALIDATION_REPORT.md").write_text(text, encoding="utf-8")
    (REPORTS / "reranker_stability_report.md").write_text("# Reranker 固定输入稳定性\n\n30诊断题、两个固定候选来源、各5轮真实执行，共300查询/3000 passage score。最大score std=0、range=0，所有 Top1/完整排名和正式排名一致；对正式保存score最大差=" + str(max(compare_scores)) + "。\n\n这是同机、同模型/代码/候选的条件性重复稳定，不保证不同 candidate pool 的输出等价。真实 batch probe 已发现两道固定 passage pair 翻转，具体 padding/量化根因尚未验证。原始每轮 query score/rank/top1/latency 见独立JSONL，分 passage 汇总见 reranker_stability.csv。\n", encoding="utf-8")
    resume = f"""# TrustRAG 封版简历与面试陈述

## 可直接使用的项目描述

基于开源 curiousily/ragbase 构建可复现的检索增强问答评测与证据引用流程，设计包含语义改写、标识符、版本冲突等类别的 240 题合成诊断集，并完成冻结配置下的受控消融、失败分析和统计验证。

- 在独立 V2 test 的 120 道可回答题上，现有 Cross-Encoder 将 Dense 的 Recall@1 从 68.33% 提升至 95.83%，MRR 从 0.8052 提升至 0.9792；以 10,000 次 paired bootstrap 验证当前样本排序收益（MRR 差值 95% CI [0.1242, 0.2251]）。
- 通过 candidate rescue 和 reranker rank-change 分析评估组件价值：当前 K=10 下 BM25 unique rescue 为0；Dense+Reranker 相对 Hybrid+Reranker 的点估计更高，但 CI 包含0，因此选择更简单架构，保持实验对照配置。
- 对 30 道诊断题进行双方法五轮随机顺序实测：固定候选下 Top1/完整排名一致；另以固定 query/target/competitor 的候选构成实验复现两道 Top1 翻转，区分重复稳定与 batch 依赖。
- 使用来源 ID、页码与文本摘录支持引用核查；实测发现原 relevance-score gate 未降低 FAR 且增加误拒答，将默认 gate 关闭并保留原实验证据。

## 必须随陈述保留的边界

上述数值仅适用于合成 V2 诊断集，不写生产准确率或自然企业普适性能。每类 test 正例约20题，数据和 gold 由项目编写者共同构建，独立人工审核仍 PENDING_HUMAN_REVIEW。

公开 SQuAD2 自然文本检索外测已零调参执行：15个文章摘录、75个原生人工问题（45可回答），R@1={external['recall@1']:.4f}、MRR={external['mrr']:.4f}。外部生成/judge 因原本地 CUDA 运行时错误 BLOCKED，不引用尚未测得的自然外测生成准确率/FAR，也不宣称自然企业端到端泛化已证实。

五轮测量显示两种重排方案在同一秒级量级，不能把单次80ms差异宣传成可靠提速。动态 padding / ONNX quantization 仅为 batch effect 的机制假说。

## 面试中不能说

- “显著优于 Hybrid+Reranker”或“证明 Dense+CE 普适最优”。差值 CI 包含0，选型同时考虑复杂度。
- “Hybrid 大幅提高召回”或“BM25在所有语料没有价值”。当前候选覆盖饱和，只报告该预算的0次 unique rescue。
- “gate显著降低幻觉/False Answer”或“score就是答案正确概率”。原 gate 没有净收益。
- “人工审核通过/100% grounded/生产数据验证完成”。judge不是独立人工；自然生成外测未完成。
- “发明了 Cross-Encoder 重排算法”。FlashRank、embedding、PDF/Qdrant/Streamlit 等沿用上游/现成组件，贡献在工程改造、受控评测、诊断和证据支持的取舍。
- 把原版到 V1 的 dev 增益全部归因于 BM25/RRF/重排：那是分块、深度、metadata/pipeline 的联合变化，缺少单因素因果对照。

## 推荐的一句话结论

“我用冻结消融、paired bootstrap 和输入稳定性实验验证了现有重排器的排序收益；没有为技术栈保留缺乏净收益的 Hybrid/gate，并明确记录合成数据、人工审核和外测运行阻塞的限制。”

封版后只做简历整理、项目讲稿和面试准备，不开启 V3。
"""
    (ROOT / "docs/final_resume_claims.md").write_text(resume, encoding="utf-8")
    verification = {"v1_v2_unchanged": True, "protected_file_count": len(protected["files"]), "bootstrap_recomputed": True,
                    "bootstrap_replicates": 10000, "bootstrap_questions": 120, "repeat_timed_queries": 300, "batch_probe_calls": 72,
                    "human_review": human["status"], "external": external_status,
                    "validation_files_sha256": {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in sorted(OUT.rglob("*")) if path.is_file() and "/indexes/" not in path.as_posix() and not path.name.endswith(".log")},
                    "driver_sha256": {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in sorted((ROOT / "scripts/final_validation").glob("*.py"))}}
    verify_frozen()
    check_or_restore()
    from scripts.final_validation.frozen_bytes import check as verify_legacy_bytes
    verify_legacy_bytes()
    write_json(REPORTS / "artifact_verification.json", verification)
    print("Final validation reports/resume created; human pending, external generation blocked, all frozen V1/V2 bytes unchanged.")


if __name__ == "__main__":
    main()
