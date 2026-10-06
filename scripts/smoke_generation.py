"""Real generator/judge smoke test on dev examples only, before formal test freeze."""

import json

from ragbase.config import load_config
from ragbase.evaluation.artifacts import ROOT, write_json
from ragbase.evaluation.benchmark import read_jsonl, write_jsonl
from ragbase.evaluation.judge import GenerationJudge
from ragbase.generation.generator import AnswerGenerator
from ragbase.schema import RetrievalResult


def main():
    config = load_config(ROOT / "configs/hybrid_reranker.yaml")
    directory = ROOT / "experiments/hybrid_reranker/dev"
    rows = {row["id"]: row for row in read_jsonl(directory / "benchmark_aligned.jsonl")}
    chunks = {chunk["chunk_id"]: chunk for chunk in read_jsonl(directory / "chunks.jsonl")}
    predictions = read_jsonl(directory / "retrieval_predictions.jsonl")
    samples = [row for row in predictions if row["answerable"]][:3] + [row for row in predictions if not row["answerable"]][:3]
    generator, judge = AnswerGenerator(config), GenerationJudge(config)
    outputs = []
    for prediction in samples:
        row = rows[prediction["id"]]
        results = [RetrievalResult(**result, text=chunks[result["chunk_id"]]["text"]) for result in prediction["results"]]
        answer = generator.generate(row["question"], results)
        judgment = judge.evaluate(row, answer)
        outputs.append({"id": row["id"], "question": row["question"], "gold_answer": row["answer"], "answerable": row["answerable"],
                        **answer.to_dict(), "judge": judgment})
        write_jsonl(ROOT / "experiments/smoke_generation/dev_predictions.jsonl", outputs)
        print(json.dumps({"id": row["id"], "answer": answer.answer, "gate": answer.gate, "judge": {key: judgment.get(key) for key in ["status", "answer_correct", "grounded", "citations_supported", "reason"]}}, ensure_ascii=False), flush=True)
    write_json(ROOT / "experiments/smoke_generation/config.json", config.to_dict())


if __name__ == "__main__":
    main()
