"""Fixed-model, fixed-prompt LLM judge. Its labels are fallible, not gold truth."""

import hashlib
import json
import re
import time

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from ragbase.generation.prompt import JUDGE_SYSTEM_PROMPT


def parse_judge_output(raw):
    text = raw.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    data = json.loads(text)
    for key in ["answer_correct", "grounded", "citations_supported"]:
        if not isinstance(data.get(key), bool):
            raise ValueError(f"Judge field {key} must be boolean")
    if not isinstance(data.get("reason"), str):
        raise ValueError("Judge reason must be text")
    return data


class GenerationJudge:
    def __init__(self, config, llm=None):
        self.config = config
        generation = config.generation
        self.llm = llm if llm is not None else ChatOllama(model=generation.judge_model, base_url=generation.base_url,
                                                        temperature=0.0, num_predict=generation.judge_max_tokens,
                                                        num_ctx=generation.context_size, format="json", keep_alive="1h")

    def evaluate(self, row, output):
        if output.abstained:
            return {"status": "not_applicable", "reason": "System abstained; gold answerability evaluates this decision."}
        cited = set(output.citation_validation["cited_ids"])
        data = {"question": row["question"], "reference_answer": row["answer"], "answer": output.answer,
                "cited_sources": [source for source in output.sources if source["source_id"] in cited]}
        human = json.dumps(data, ensure_ascii=False)
        prompt_hash = hashlib.sha256((JUDGE_SYSTEM_PROMPT + human).encode()).hexdigest()
        start = time.perf_counter()
        response = self.llm.invoke([SystemMessage(content=JUDGE_SYSTEM_PROMPT), HumanMessage(content=human)], seed=42)
        elapsed = (time.perf_counter() - start) * 1000
        raw = response.content
        metadata = dict(response.response_metadata or {})
        result = {"model": self.config.generation.judge_model, "temperature": 0.0, "seed": 42, "prompt_sha256": prompt_hash,
                  "raw_output": raw, "latency_ms": elapsed, "input_tokens": int(metadata.get("prompt_eval_count", 0) or 0),
                  "output_tokens": int(metadata.get("eval_count", 0) or 0), "model_metadata": metadata,
                  "method": "LLM-as-a-Judge, same model family as generator; not absolute ground truth"}
        try:
            result.update(status="ok", **parse_judge_output(raw))
        except (ValueError, json.JSONDecodeError) as error:
            result.update(status="invalid_output", parse_error=str(error))
        return result
