import json

import yaml

from ragbase.config import load_config
from ragbase.evaluation.artifacts import ROOT, write_json
from ragbase.evaluation.benchmark import read_jsonl, sha256_file
from ragbase.generation.answerability import calibrate


def main():
    summary = {}
    for name in ["baseline", "dense_reranker", "bm25", "hybrid", "hybrid_reranker"]:
        config_path = ROOT / "configs" / f"{name}.yaml"
        config = load_config(config_path)
        directory = ROOT / "experiments" / config.name / "dev"
        prediction_path = directory / "retrieval_predictions.jsonl"
        resolved = json.loads((directory / "resolved_config.json").read_text(encoding="utf-8"))
        if resolved["split"] != "dev":
            raise ValueError("Threshold calibration accepts dev predictions only")
        if resolved["retrieval"] != config.to_dict()["retrieval"] or resolved["chunking"] != config.to_dict()["chunking"]:
            raise ValueError("Calibration retrieval config differs from saved dev predictions")
        calibration = calibrate(read_jsonl(prediction_path))
        calibration.update(predictions_sha256=sha256_file(prediction_path), benchmark_sha256=resolved["benchmark_sha256"],
                           index_id=resolved["index"]["index_id"], method=config.name, retrieval_config=resolved["retrieval"])
        calibration_path = directory / "calibration.json"
        write_json(calibration_path, calibration)
        data = config.to_dict()
        data["answerability"] = {"enabled": True, "feature": calibration["selected_feature"], "threshold": calibration["threshold"],
                                 "calibration_file": calibration_path.relative_to(ROOT).as_posix()}
        config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")
        summary[config.name] = {key: calibration[key] for key in ["selected_feature", "threshold", "selected_metrics", "best_by_feature", "index_id"]}
        print(f"{config.name}: {calibration['selected_feature']} >= {calibration['threshold']:.6g}; dev F1={calibration['selected_metrics']['f1']:.4f}", flush=True)
    write_json(ROOT / "reports/answerability_calibration.json", summary)
    lines = ["# Evidence gate calibration (dev only)", "", "Each retrieval mode is calibrated on its own score scale. Dense, BM25 and RRF raw scores are never compared across scales. The main Hybrid + Reranker uses cross-encoder evidence. Each feature scans all distinct observed boundaries, including an all-refuse boundary. F1 is the predeclared objective, with false-answer/refusal tie breakers. These are retrieval-gate predictions, not final generation outcomes or probabilities.", "", "| Method | Feature | Threshold | Precision | Recall | F1 | False answer rate | False refusal rate |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, result in summary.items():
        metric = result["selected_metrics"]
        lines.append(f"| {name} | {result['selected_feature']} | {result['threshold']:.8g} | {metric['precision']:.4f} | {metric['recall']:.4f} | {metric['f1']:.4f} | {metric['false_answer_rate']:.4f} | {metric['false_refusal_rate']:.4f} |")
    (ROOT / "reports/answerability_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
