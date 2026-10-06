# Failure analysis

Population: 120 formal test questions. 6 questions have at least one automatic failure label. Categories are multi-label: percentages use all questions and can sum above 100%. LLM-derived labels are hypotheses, not verified human ground truth.

| Category | Count | Percentage | Possible cause | Review / improvement |
| --- | --- | --- | --- | --- |
| Retrieval Miss | 0 | 0.00% | Gold evidence absent from the candidate pool. | Inspect lexical mismatch and candidate coverage on dev. |
| Ranking Error | 0 | 0.00% | Gold candidate is available but outside the generation context depth. | Inspect reranker order and final context depth on dev. |
| Chunk Boundary Error | 0 | 0.00% | Evidence span is not preserved by the chunk boundaries. | Inspect gold alignment and overlap; no cross-chunk gold cases are labeled in v1. |
| Insufficient Context | 0 | 0.00% | A selected gold chunk's quoted excerpt omits the gold span. | Inspect the context budget and excerpt boundaries on dev. |
| Generation Hallucination | 0 | 0.00% | The fixed LLM judge marked a published claim unsupported. | Manually check the claim/source pair; judge labels are fallible. |
| Wrong Citation | 0 | 0.00% | Invalid reference or citation support failure. | Inspect exact cited source scope and raw versus published output. |
| False Refusal | 6 | 5.00% | Answerable gold question received an abstention. | Inspect evidence score, gate, source coverage and model refusal separately. |
| False Answer | 0 | 0.00% | Unanswerable gold question received a published answer. | Inspect relevance-versus-answerability and missing-entity/exception inference. |
| Generation Error | 0 | 0.00% | Incorrect answer despite claims judged grounded. | Inspect scope, units and whether the response answers the actual question. |
| Judge Failure | 0 | 0.00% | Judge output could not be parsed or validated. | Review saved raw judge output; do not treat it as negative ground truth. |

## Representative cases

- `q0202` — False Refusal (answerability)
  Question: How many days off are allowed after an immediate family bereavement?
  Gold: 5 working days; output: I couldn't find sufficient evidence in the current knowledge base to answer this question reliably.
  Gate: 0.016950911 / 0.03984235227108002; reason: insufficient_evidence
- `q0404` — False Refusal (answerability)
  Question: After how much inactivity should a workstation lock?
  Gold: 5 minutes; output: I couldn't find sufficient evidence in the current knowledge base to answer this question reliably.
  Gate: 0.00078813982 / 0.03984235227108002; reason: insufficient_evidence
- `q0103` — False Refusal (answerability)
  Question: How much unused vacation can I move into the next year?
  Gold: 5 working days; output: I couldn't find sufficient evidence in the current knowledge base to answer this question reliably.
  Gate: 0.0012108623 / 0.03984235227108002; reason: insufficient_evidence
- `q0305` — False Refusal (answerability)
  Question: How quickly does Finance review a complete expense claim?
  Gold: 7 business days; output: I couldn't find sufficient evidence in the current knowledge base to answer this question reliably.
  Gate: 0.9837842 / 0.03984235227108002; reason: model_refusal
- `q0505` — False Refusal (answerability)
  Question: How far ahead must I seek permission to work remotely abroad?
  Gold: 14 calendar days; output: I couldn't find sufficient evidence in the current knowledge base to answer this question reliably.
  Gate: 0.0062405728 / 0.03984235227108002; reason: insufficient_evidence
- `q0310` — False Refusal (answerability)
  Question: What kind of receipt is needed for reimbursement?
  Gold: an itemized receipt; output: I couldn't find sufficient evidence in the current knowledge base to answer this question reliably.
  Gate: 0.0036354084 / 0.03984235227108002; reason: insufficient_evidence

V1 contains single-page fact gold; zero chunk-boundary labels do not establish robustness to cross-page or multi-hop evidence. Review the prepared sample pack independently before treating model-judge labels as ground truth.
