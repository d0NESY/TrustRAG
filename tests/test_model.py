import json

from langchain_core.messages import HumanMessage

from ragbase.config import ExperimentConfig
from ragbase.model import create_llm


def test_real_ollama_adapter_passes_seed_and_output_budget_to_api(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        encoding = "utf-8"

        def iter_lines(self, **kwargs):
            yield json.dumps({"message": {"role": "assistant", "content": "Ten days. [S1]"}, "done": True,
                              "prompt_eval_count": 10, "eval_count": 5})

    def post(url, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr("langchain_community.llms.ollama.requests.post", post)
    config = ExperimentConfig()
    reply = create_llm(config).invoke([HumanMessage(content="Test question")], seed=config.generation.seed)
    assert reply.content == "Ten days. [S1]"
    assert captured["options"]["seed"] == 42
    assert captured["options"]["num_predict"] == config.generation.max_tokens
    assert captured["options"]["num_ctx"] == config.generation.context_size
