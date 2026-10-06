# 独立人工 Audit 操作说明

填写 human_audit_template.csv 的四个 human 字段：1 / 0 / UNCERTAIN；保留原样本和 gold 不改，疑似标注错误填写 human_answerable_label_valid=0 或 UNCERTAIN 并解释。reviewer_id 填真实独立 reviewer 标识。

请先看问题、参考答案、实际输出和完整来源摘录，再查看模型 judge 记录，避免先看 judge 标签产生锚定偏差。

- human_answer_correct：回答是否正确回应所问事实；拒答是否恰当也在此评估。
- human_answerable_label_valid：原 answerable_gold 标注是否有效；1=同意，0=不同意。
- human_grounded：已发布陈述是否获得提供来源支持；拒答若无法评估可写 UNCERTAIN。
- human_citation_valid：引用是否支持陈述且可定位；无引用的拒答可写 UNCERTAIN。

这是目的性抽样，包含失败与边界样本，人工准确率只描述该审核包，不能当作全量 test 的随机抽样准确率。Codex 不填写任何人工标签。独立 reviewer 完成后运行 python -m scripts.final_validation.human_audit 汇总，UNKNOWN/空白不得自动变成 0。
