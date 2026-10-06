# Sample review

Codex inspected 20 saved test examples: all 6 automatically labeled main-pipeline failures and 14 seeded controls. This is an agent review, not an independent human audit. Per-example notes are in codex_sample_review.csv.

Five gate refusals have explicit supporting policy facts. One model refusal (q0305) exposes a gold-scope ambiguity: the policy states a complete-claim review target of 7 business days, while the question names Finance, which is not explicitly assigned in that source. The original gold and formal test scores remain unchanged; a future benchmark version should either specify the reviewer in the source or ask about the review target without an unsupported actor.

The inspected published answers match quoted numeric values/units and policy scope. Negative controls ask for missing future dates, unsupported groups or negotiated terms and correctly abstain. This small sample does not validate every judge label or establish natural-document reliability. Independent human review remains pending in review_samples.jsonl.
