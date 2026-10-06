# 盲审操作

优先填写 human_audit_blind.csv。表中隐藏模型 judge、自动失败分类、gate 条件与最终系统标签，提供原问题、gold、实际回答、全部五个来源摘录、引用 ID 和完整 gold source。请独立判断后再查看 comparison。

四个 human 字段仅允许 `1` / `0` / `UNCERTAIN`；human_notes 为自由解释，不受枚举限制。reviewer_id 填真实独立审核人，reviewed_at 填实际时间。不要改变问题、gold、模型输出或来源。

- human_answer_correct：是否真正回应所问事实；拒答是否恰当，而不是仅“听起来合理”。
- human_answerable_label_valid：原 gold_answerable 标签是否合理；1=同意原标签，0=不同意。
- human_grounded：核心事实是否在引用证据中得到支持；不能评估时 UNCERTAIN。
- human_citation_valid：引用是否支持对应回答并可定位；无引用拒答可写 UNCERTAIN。

28 条是 error-oriented/manual audit，不是完整 test 的无偏准确率估计。自动检查、Codex 判断、LLM judge 都不构成独立人工审核。完整真人标签回来后运行 `python -m scripts.release.audit`，才生成 human_audit_comparison.csv、HUMAN_AUDIT_FINAL.md 和完整 disagreement 列表。不计算不合适的 Kappa。
