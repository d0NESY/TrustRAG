from dataclasses import replace

from langchain_core.messages import AIMessage

from ragbase.config import ExperimentConfig, AnswerabilityConfig
from ragbase.generation.generator import AnswerGenerator
from ragbase.generation.answerability import ABSTENTION_TEXT
from ragbase.schema import RetrievalResult


class LLMStub:
    def __init__(self, answer):
        self.answer = answer
        self.calls = 0

    def invoke(self, messages, **kwargs):
        self.calls += 1
        return AIMessage(content=self.answer, response_metadata={"prompt_eval_count": 10, "eval_count": 5})


def evidence(score=0.9):
    return [RetrievalResult("chunk", "doc", score, 1, "Employees receive 10 paid sick days.",
                            {"filename": "policy.pdf", "page": 2, "start_index": 0})]


def test_gate_rejects_without_any_llm_call():
    llm = LLMStub("An unsupported answer. [S1]")
    config = replace(ExperimentConfig(), answerability=AnswerabilityConfig(enabled=True, threshold=0.95))
    output = AnswerGenerator(config, llm).generate("question", evidence())
    assert output.abstained
    assert output.answer == ABSTENTION_TEXT
    assert llm.calls == 0


def test_valid_cited_answer_preserves_page_and_usage():
    output = AnswerGenerator(ExperimentConfig(), LLMStub("10 paid sick days. [S1]")).generate("question", evidence())
    assert not output.abstained
    assert output.sources[0]["page"] == 2
    assert output.input_tokens == 10
    assert output.output_tokens == 5


def test_unknown_citation_and_refusal_never_leak_extra_answer_text():
    output = AnswerGenerator(ExperimentConfig(), LLMStub("Invented answer. [S99]")).generate("question", evidence())
    assert output.abstained and output.refusal_reason == "invalid_citation"
    assert output.raw_answer == "Invented answer. [S99]"
    output = AnswerGenerator(ExperimentConfig(), LLMStub(ABSTENTION_TEXT + " However, the price is $99.")).generate("question", evidence())
    assert output.answer == ABSTENTION_TEXT
