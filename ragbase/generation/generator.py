from dataclasses import asdict, dataclass
import hashlib
import json
import time

from langchain_core.messages import HumanMessage, SystemMessage

from ragbase.generation.answerability import ABSTENTION_TEXT, AnswerabilityGate
from ragbase.generation.citation import CitationValidation, format_sources, make_sources, validate_citations
from ragbase.generation.prompt import SYSTEM_PROMPT
from ragbase.model import create_llm


@dataclass
class GeneratedAnswer:
    answer: str
    raw_answer: str
    abstained: bool
    refusal_reason: str | None
    gate: dict
    sources: list[dict]
    citation_validation: dict
    generation_latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None
    prompt_sha256: str | None
    model_metadata: dict

    def to_dict(self):
        return asdict(self)


class AnswerGenerator:
    def __init__(self, config, llm=None):
        self.config = config.validate()
        self.llm = llm if llm is not None else create_llm(config)
        self.gate = AnswerabilityGate(config.answerability)

    def generate(self, question, results):
        decision = self.gate.decide(results)
        sources = make_sources(results, self.config.retrieval.context_top_k, self.config.generation.context_chars_per_source)
        if not decision.sufficient:
            return GeneratedAnswer(ABSTENTION_TEXT, "", True, decision.reason, asdict(decision), [source.to_dict() for source in sources],
                                   asdict(CitationValidation(False, [], [], 0, True)), 0.0, 0, 0, 0.0 if self.config.generation.provider == "groq" else None, None, {})
        human = f"Sources:\n{format_sources(sources)}\n\nQuestion: {question}"
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=human)]
        prompt_hash = hashlib.sha256(json.dumps([SYSTEM_PROMPT, human, self.config.llm_model, self.config.to_dict()["generation"]], sort_keys=True).encode()).hexdigest()
        start = time.perf_counter()
        response = self.llm.invoke(messages, seed=self.config.generation.seed) if self.config.generation.provider == "ollama" else self.llm.invoke(messages)
        elapsed = (time.perf_counter() - start) * 1000
        raw = response.content.strip()
        metadata = dict(response.response_metadata or {})
        usage = metadata.get("token_usage", {})
        input_tokens = int(metadata.get("prompt_eval_count", usage.get("prompt_tokens", 0)) or 0)
        output_tokens = int(metadata.get("eval_count", usage.get("completion_tokens", 0)) or 0)
        citations = validate_citations(raw, [source.source_id for source in sources])
        is_refusal = raw == ABSTENTION_TEXT or ABSTENTION_TEXT.lower().rstrip(".") in raw.lower()
        reason = "model_refusal" if is_refusal else ("invalid_citation" if not citations.valid else None)
        # Refusal is enforced after the gate and after malformed/absent citations.
        # Raw output remains saved for audit, rather than silently inventing references.
        answer = ABSTENTION_TEXT if reason else raw
        generation = self.config.generation
        cost = None
        if generation.provider == "groq" and generation.input_cost_per_million is not None and generation.output_cost_per_million is not None:
            cost = (input_tokens * generation.input_cost_per_million + output_tokens * generation.output_cost_per_million) / 1_000_000
        return GeneratedAnswer(answer, raw, bool(reason), reason, asdict(decision), [source.to_dict() for source in sources], asdict(citations),
                               elapsed, input_tokens, output_tokens, cost, prompt_hash, metadata)
