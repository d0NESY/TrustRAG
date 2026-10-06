"""Readable blind audit; comparison becomes available only after human review."""

import csv
import json
from statistics import mean

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl
from scripts.final_validation.common import csv_write, table
from scripts.release.common import ROOT, RELEASE, begin, verify, write_md

LABELS = ["human_answer_correct", "human_answerable_label_valid", "human_grounded", "human_citation_valid"]


def source_text(source):
    return f"[{source['source_id']}] {source['filename']} / page {source['page']}\n{source['text']}"


def main():
    begin()
    blind = RELEASE / "human_audit_blind.csv"
    with (ROOT / "reports/final_validation/human_audit_template.csv").open(encoding="utf-8-sig", newline="") as stream:
        prior = list(csv.DictReader(stream))
    with (ROOT / "reports/human_review_template.csv").open(encoding="utf-8-sig", newline="") as stream:
        legacy = list(csv.DictReader(stream))
    metadata = json.loads((ROOT / "reports/final_validation/human_audit_metadata.json").read_text(encoding="utf-8"))
    meta = {row["sample_key"]: row for row in metadata["samples"]}
    chunks = {row["chunk_id"]: row for row in read_jsonl(ROOT / "experiments/v2/test/hybrid_reranker/chunks.jsonl")}
    generated = {condition: {row["id"]: row for row in read_jsonl(ROOT / "experiments/v2/test" / condition / "generation_predictions.jsonl")}
                 for condition in ["G0_prompt_only", "G1_current_v1_gate"]}
    if not blind.exists():
        rows = []
        for row in prior:
            sources = json.loads(row["retrieved_sources"])
            recorded = generated[row["condition"]][row["question_id"]]
            gold = [chunks[key] for key in recorded["gold_chunk_ids"]]
            rows.append({"sample_key": row["sample_key"], "question_id": row["question_id"], "category": row["category"],
                         "question": row["question"], "gold_answer": row["gold_answer"], "gold_answerable": row["answerable_gold"],
                         "model_answer": row["model_answer"],
                         **{f"retrieved_source_{number}": source_text(sources[number - 1]) if number <= len(sources) else "" for number in range(1, 6)},
                         "cited_source_ids": ", ".join(recorded["citation_validation"]["cited_ids"]),
                         "gold_source": "\n\n".join(f"{g['metadata']['filename']} / page {g['metadata']['page']}\n{g['text']}" for g in gold) or "No positive gold source; review whether the requested fact is absent.",
                         **{field: row.get(field, "") for field in LABELS}, "human_notes": row.get("human_notes", ""),
                         "reviewer_id": row.get("reviewer_id", ""), "reviewed_at": ""})
        csv_write(blind, rows)
    with blind.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for field in LABELS:
            row[field] = row[field].strip()
            if row[field] not in {"", "0", "1", "UNCERTAIN"}:
                raise ValueError(f"Unsupported human label: {row['sample_key']}/{field}")
    complete = bool(rows) and all(row["reviewer_id"].strip() and all(row[field] for field in LABELS) for row in rows)
    filled = sum(bool(row[field]) for row in rows for field in LABELS)
    old_count = sum(any(row.get(field, "").strip() for field in ["human_correctness", "human_groundedness", "human_citation_valid", "human_notes"]) for row in legacy)
    status = "COMPLETE" if complete else "PENDING_HUMAN_REVIEW"
    write_json(RELEASE / "human_audit_status.json", {"status": status, "rows": len(rows), "filled_human_cells": filled,
               "required_human_cells": len(rows) * 4, "legacy_filled_rows": old_count,
               "comparison_created": complete, "reviewer_identity_required": True,
               "sampling": "28 purposeful error/boundary samples; not an unbiased test-accuracy estimate."})
    write_md(RELEASE / "HUMAN_AUDIT_GUIDE.md", """# 盲审操作

优先填写 human_audit_blind.csv。表中隐藏模型 judge、自动失败分类、gate 条件与最终系统标签，提供原问题、gold、实际回答、全部五个来源摘录、引用 ID 和完整 gold source。请独立判断后再查看 comparison。

四个 human 字段仅允许 `1` / `0` / `UNCERTAIN`；human_notes 为自由解释，不受枚举限制。reviewer_id 填真实独立审核人，reviewed_at 填实际时间。不要改变问题、gold、模型输出或来源。

- human_answer_correct：是否真正回应所问事实；拒答是否恰当，而不是仅“听起来合理”。
- human_answerable_label_valid：原 gold_answerable 标签是否合理；1=同意原标签，0=不同意。
- human_grounded：核心事实是否在引用证据中得到支持；不能评估时 UNCERTAIN。
- human_citation_valid：引用是否支持对应回答并可定位；无引用拒答可写 UNCERTAIN。

28 条是 error-oriented/manual audit，不是完整 test 的无偏准确率估计。自动检查、Codex 判断、LLM judge 都不构成独立人工审核。完整真人标签回来后运行 `python -m scripts.release.audit`，才生成 human_audit_comparison.csv、HUMAN_AUDIT_FINAL.md 和完整 disagreement 列表。不计算不合适的 Kappa。
""")
    if complete:
        summaries, comparison, disagreements = [], [], []
        for field, title in zip(LABELS, ["Human Answer Accuracy", "Gold Label Agreement", "Human Groundedness Rate", "Human Citation Validity Rate"]):
            values = [int(row[field]) for row in rows if row[field] in {"0", "1"}]
            summaries.append({"metric": title, "value": mean(values) if values else None, "certain_count": len(values), "uncertain_count": sum(row[field] == "UNCERTAIN" for row in rows)})
        for row in rows:
            judge = meta[row["sample_key"]]["judge"]
            comparison.append({**row, "llm_judge_status": judge["status"], "llm_judge_correctness": judge.get("answer_correct"), "llm_judge_groundedness": judge.get("grounded"), "llm_judge_citation_valid": judge.get("citations_supported")})
            for field, key in [("human_answer_correct", "answer_correct"), ("human_grounded", "grounded"), ("human_citation_valid", "citations_supported")]:
                if row[field] in {"0", "1"} and judge.get("status") == "ok" and bool(int(row[field])) != judge[key]:
                    disagreements.append({"sample_key": row["sample_key"], "question_id": row["question_id"], "field": field, "human": row[field], "judge": int(judge[key]), "notes": row["human_notes"]})
        csv_write(RELEASE / "human_audit_comparison.csv", comparison)
        csv_write(RELEASE / "human_judge_disagreements.csv", disagreements, ["sample_key", "question_id", "field", "human", "judge", "notes"])
        agreements = []
        for field, key in [("human_answer_correct", "answer_correct"), ("human_grounded", "grounded"), ("human_citation_valid", "citations_supported")]:
            comparable = [bool(int(row[field])) == meta[row["sample_key"]]["judge"][key] for row in rows if row[field] in {"0", "1"} and meta[row["sample_key"]]["judge"].get("status") == "ok"]
            agreements.append([field, mean(comparable) if comparable else None, len(comparable)])
        text = "# Human Audit FINAL\n\n状态：COMPLETE（表格已填且记录 reviewer 身份，独立性仍由真实 reviewer 声明保证）。\n\n"
        text += table(["metric", "value", "certain N", "uncertain N"], [[r[k] for k in ["metric", "value", "certain_count", "uncertain_count"]] for r in summaries])
        text += "\n\n" + table(["Human vs Judge field", "agreement", "comparable N"], agreements)
        text += "\n\n这是目的性审核包的描述统计，非完整 test 的无偏估计。UNCERTAIN 与空白不当作0；not_applicable judge 不参与一致性。所有分歧逐行保存。\n"
        write_md(RELEASE / "HUMAN_AUDIT_FINAL.md", text)
    else:
        write_md(RELEASE / "HUMAN_AUDIT_PENDING.md", f"# Human Audit：PENDING_HUMAN_REVIEW\n\n盲审表 {len(rows)} 条，人工标签 {filled}/{len(rows) * 4}。未取得完整独立真人审核，不生成带 judge 结果的 comparison 版本，也不报告人工准确率。旧审核表保留不变。\n")
    verify()
    print(f"Release blind audit {status}: {len(rows)} rows, {filled} labels.")


if __name__ == "__main__":
    main()
