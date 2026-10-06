"""Prepare a blind-to-judge audit packet; never generate human labels."""

import csv
import json

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl, sha256_file
from scripts.final_validation.common import ROOT, REPORTS, prepare, verify_frozen, csv_write, table

LABELS = ["human_answer_correct", "human_answerable_label_valid", "human_grounded", "human_citation_valid"]


def prepare_packet():
    prepare()
    target = REPORTS / "human_audit_template.csv"
    if target.exists():
        return
    with (ROOT / "reports/human_review_template.csv").open(encoding="utf-8-sig", newline="") as stream:
        legacy = list(csv.DictReader(stream))
    legacy_fields = ["human_correctness", "human_groundedness", "human_citation_valid", "human_notes"]
    legacy_filled = sum(any(row.get(field, "").strip() for field in legacy_fields) for row in legacy)
    review_samples = read_jsonl(ROOT / "reports/review_samples.jsonl")
    source = {condition: read_jsonl(ROOT / "experiments/v2/test" / condition / "generation_predictions.jsonl")
              for condition in ["G0_prompt_only", "G1_current_v1_gate"]}
    chosen, used = [], set()
    def choose(condition, predicate, count, reason):
        if count <= 0:
            return
        options = sorted([row for row in source[condition] if predicate(row)], key=lambda row: row["id"])
        for row in options:
            key = condition, row["id"]
            if key in used:
                continue
            chosen.append((condition, row, reason))
            used.add(key)
            count -= 1
            if count == 0:
                break
    choose("G0_prompt_only", lambda r: not r["answerable"] and not r["abstained"], 2, "automatic False Answer")
    choose("G0_prompt_only", lambda r: r["answerable"] and not r["abstained"] and r["judge"].get("answer_correct") is False, 3, "LLM judge flags incorrect; not a human conclusion")
    choose("G1_current_v1_gate", lambda r: r["answerable"] and r["abstained"], 4, "automatic False Refusal")
    choose("G0_prompt_only", lambda r: not r["answerable"] and r["abstained"], 4, "correct refusal under frozen gold")
    choose("G0_prompt_only", lambda r: bool(set(r["citation_validation"]["cited_ids"])) and any(s["source_id"] in r["citation_validation"]["cited_ids"] and s["chunk_id"] not in r["gold_chunk_ids"] for s in r["sources"]), 3, "citation boundary: cited source outside gold IDs")
    for category in ["version_conflict", "hard_negative", "semantic", "exact_term", "numeric_date", "cross_document"]:
        choose("G0_prompt_only", lambda r, category=category: r["category"] == category and r["answerable"] and not r["abstained"], 2, "category coverage / published answer")
    choose("G0_prompt_only", lambda r: r["answerable"] and not r["abstained"] and r["judge"].get("answer_correct") is True, 28 - len(chosen), "LLM-judged correct candidate; requires human confirmation")
    chosen = chosen[:28]
    fields = ["question_id", "category", "question", "gold_answer", "model_answer", "retrieved_sources", "cited_sources", "answerable_gold", *LABELS, "human_notes", "condition", "sample_key", "reviewer_id"]
    rows, metadata = [], []
    for number, (condition, row, reason) in enumerate(chosen, 1):
        key = f"audit_{number:02d}"
        cited = set(row["citation_validation"]["cited_ids"])
        rows.append({"question_id": row["id"], "category": row["category"], "question": row["question"], "gold_answer": row["gold_answer"],
                     "model_answer": row["answer"], "retrieved_sources": json.dumps(row["sources"], ensure_ascii=False),
                     "cited_sources": json.dumps([s for s in row["sources"] if s["source_id"] in cited], ensure_ascii=False),
                     "answerable_gold": int(row["answerable"]), **{field: "" for field in LABELS}, "human_notes": "", "condition": condition,
                     "sample_key": key, "reviewer_id": ""})
        metadata.append({"sample_key": key, "question_id": row["id"], "condition": condition, "selection_reason": reason, "judge": row["judge"],
                         "abstained": row["abstained"], "refusal_reason": row["refusal_reason"]})
    csv_write(target, rows, fields)
    write_json(REPORTS / "human_audit_metadata.json", {"status": "PENDING_HUMAN_REVIEW", "samples": metadata,
               "legacy_review_sample_count": len(review_samples), "legacy_template_count": len(legacy), "legacy_filled_rows": legacy_filled,
               "legacy_sources_sha256": {name: sha256_file(ROOT / name) for name in ["reports/review_samples.jsonl", "reports/human_review_template.csv"]},
               "selection": "Purposeful boundary/failure/category coverage; not a random audit for population accuracy. Judge labels hidden from reviewer CSV."})
    (REPORTS / "HUMAN_AUDIT_INSTRUCTIONS.md").write_text("# 独立人工 Audit 操作说明\n\n填写 human_audit_template.csv 的四个 human 字段：1 / 0 / UNCERTAIN；保留原样本和 gold 不改，疑似标注错误填写 human_answerable_label_valid=0 或 UNCERTAIN 并解释。reviewer_id 填真实独立 reviewer 标识。\n\n请先看问题、参考答案、实际输出和完整来源摘录，再查看模型 judge 记录，避免先看 judge 标签产生锚定偏差。\n\n- human_answer_correct：回答是否正确回应所问事实；拒答是否恰当也在此评估。\n- human_answerable_label_valid：原 answerable_gold 标注是否有效；1=同意，0=不同意。\n- human_grounded：已发布陈述是否获得提供来源支持；拒答若无法评估可写 UNCERTAIN。\n- human_citation_valid：引用是否支持陈述且可定位；无引用的拒答可写 UNCERTAIN。\n\n这是目的性抽样，包含失败与边界样本，人工准确率只描述该审核包，不能当作全量 test 的随机抽样准确率。Codex 不填写任何人工标签。独立 reviewer 完成后运行 python -m scripts.final_validation.human_audit 汇总，UNKNOWN/空白不得自动变成 0。\n", encoding="utf-8")


def summarize():
    with (REPORTS / "human_audit_template.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    metadata = json.loads((REPORTS / "human_audit_metadata.json").read_text(encoding="utf-8"))
    lookup = {row["sample_key"]: row for row in metadata["samples"]}
    for row in rows:
        for field in LABELS:
            row[field] = row[field].strip()
            if row[field].strip() not in {"", "0", "1", "UNCERTAIN"}:
                raise ValueError(f"Invalid human label: {row['sample_key']}/{field}")
    complete = all(row[field].strip() and row["reviewer_id"].strip() for row in rows for field in LABELS)
    filled = sum(bool(row[field].strip()) for row in rows for field in LABELS)
    status = "COMPLETE" if complete else "PENDING_HUMAN_REVIEW"
    summaries, disagreements = [], []
    metric_names = ["Human Answer Accuracy", "Human Gold Agreement", "Human Groundedness", "Human Citation Validity"]
    for field, metric_name in zip(LABELS, metric_names):
        certain = [int(row[field]) for row in rows if row[field].strip() in {"0", "1"}]
        summaries.append({"metric": metric_name, "value": sum(certain) / len(certain) if certain else None,
                          "certain_count": len(certain), "uncertain_count": sum(row[field] == "UNCERTAIN" for row in rows)})
    comparisons = []
    for field, judge_key in [("human_answer_correct", "answer_correct"), ("human_grounded", "grounded"), ("human_citation_valid", "citations_supported")]:
        matches = []
        for row in rows:
            judge = lookup[row["sample_key"]]["judge"]
            if row[field] in {"0", "1"} and judge.get("status") == "ok":
                equal = bool(int(row[field])) == judge[judge_key]
                matches.append(equal)
                if not equal:
                    disagreements.append({"sample_key": row["sample_key"], "question_id": row["question_id"], "field": field,
                                          "human_label": row[field], "judge_label": int(judge[judge_key]), "human_notes": row["human_notes"]})
        comparisons.append({"field": field, "agreement_rate": sum(matches) / len(matches) if matches else None, "comparable_count": len(matches)})
    csv_write(REPORTS / "human_judge_disagreements.csv", disagreements, ["sample_key", "question_id", "field", "human_label", "judge_label", "human_notes"])
    write_json(REPORTS / "human_audit_status.json", {"status": status, "rows": len(rows), "filled_label_cells": filled,
               "uncertain_rows": sum(any(row[field] == "UNCERTAIN" for field in LABELS) for row in rows), "metrics": summaries, "human_vs_judge": comparisons,
               "independence": "Reviewer identity/declaration required; code does not create or infer human judgments."})
    text = f"# Human Audit 汇总\n\n状态：**{status}**。{len(rows)} 条样本，已填写人工标签 {filled}/{len(rows) * len(LABELS)}。\n\n"
    text += table(["metric", "value", "certain N", "uncertain N"], [[r["metric"], r["value"], r["certain_count"], r["uncertain_count"]] for r in summaries])
    text += "\n\n" + table(["field", "Human/LLM agreement", "comparable N"], [[r["field"], r["agreement_rate"], r["comparable_count"]] for r in comparisons])
    text += "\n\n未填写/UNCERTAIN 不作为错误或正确。LLM judge 为 not_applicable 的拒答不参与 judge 一致性计算。审核包为目的性样本，不代表全量总体指标；独立性不能仅凭表格非空推断。\n"
    (REPORTS / "human_audit_summary.md").write_text(text, encoding="utf-8")
    if not complete:
        (REPORTS / "HUMAN_AUDIT_PENDING.md").write_text("# Human Audit：PENDING_HUMAN_REVIEW\n\n未取得真实独立 reviewer 的完整标签。已提供 28 条失败/边界/类别覆盖样本，所有新人工字段初始为空；Codex 不填写标签、不声称完成。\n\n填写 human_audit_template.csv（1/0/UNCERTAIN）并记录 reviewer_id 后再汇总。原 V1 审阅文件保持原样，当前旧模板也未含人工结果。\n", encoding="utf-8")
    verify_frozen()
    print(f"Human audit {status}: {len(rows)} samples, {filled} human labels.")


def main():
    prepare_packet()
    summarize()


if __name__ == "__main__":
    main()
