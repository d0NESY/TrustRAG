from dataclasses import dataclass
import math
from statistics import mean


ABSTENTION_TEXT = "I couldn't find sufficient evidence in the current knowledge base to answer this question reliably."


def evidence_features(scores):
    scores = [float(score) for score in scores]
    if any(not math.isfinite(score) for score in scores):
        raise ValueError("Nonfinite evidence score")
    if not scores:
        return {"top1": 0.0, "top3_mean": 0.0, "margin": 0.0}
    return {"top1": scores[0], "top3_mean": mean(scores[:3]), "margin": scores[0] - (scores[1] if len(scores) > 1 else 0.0)}


def answerability_metrics(gold, predicted):
    if len(gold) != len(predicted):
        raise ValueError("Gold/prediction lengths differ")
    tp = sum(bool(g) and bool(p) for g, p in zip(gold, predicted))
    fp = sum(not g and bool(p) for g, p in zip(gold, predicted))
    fn = sum(bool(g) and not p for g, p in zip(gold, predicted))
    tn = sum(not g and not p for g, p in zip(gold, predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "false_answer_rate": fp / (fp + tn) if fp + tn else None,
            "false_refusal_rate": fn / (fn + tp) if fn + tp else None,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn, "count": len(gold)}


@dataclass(frozen=True)
class GateDecision:
    sufficient: bool
    confidence: float
    threshold: float | None
    feature: str
    reason: str


class AnswerabilityGate:
    def __init__(self, config):
        self.config = config
        if config.enabled and (config.threshold is None or not math.isfinite(config.threshold)):
            raise ValueError("Gate needs a finite dev-calibrated threshold")

    def decide(self, results):
        confidence = evidence_features([result.score for result in results])[self.config.feature]
        enough = bool(results) and (not self.config.enabled or confidence >= self.config.threshold)
        reason = "no_evidence" if not results else ("gate_disabled" if not self.config.enabled else ("sufficient_evidence" if enough else "insufficient_evidence"))
        return GateDecision(enough, confidence, self.config.threshold, self.config.feature, reason)


def calibrate(predictions):
    gold = [row["answerable"] for row in predictions]
    if not any(gold) or all(gold):
        raise ValueError("Calibration requires answerable AND unanswerable dev questions")
    features = [evidence_features([result["score"] for result in row["results"]]) for row in predictions]
    scans, best = {}, {}
    for feature in ["top1", "top3_mean", "margin"]:
        values = [row[feature] for row in features]
        unique = sorted(set(values))
        thresholds = [math.nextafter(unique[0], -math.inf)] + unique + [math.nextafter(unique[-1], math.inf)]
        scan = []
        for threshold in thresholds:
            decisions = [bool(row["results"]) and value >= threshold for row, value in zip(predictions, values)]
            scan.append({"threshold": threshold, **answerability_metrics(gold, decisions)})
        scans[feature] = scan
        best[feature] = max(scan, key=lambda result: (result["f1"], -result["false_answer_rate"], -result["false_refusal_rate"], result["threshold"]))
    preference = {"top1": 2, "top3_mean": 1, "margin": 0}
    selected = max(best, key=lambda feature: (best[feature]["f1"], -best[feature]["false_answer_rate"], -best[feature]["false_refusal_rate"], preference[feature]))
    return {"split": "dev", "selected_feature": selected, "threshold": best[selected]["threshold"], "selected_metrics": best[selected],
            "best_by_feature": best, "threshold_scans": scans,
            "objective": "Maximize dev F1; ties minimize false answers, then false refusals; feature ties prefer top1, top3_mean, margin.",
            "definitions": "Positive=answerable. FAR=FP/unanswerable, FRR=FN/answerable. Score is an evidence feature, not a calibrated probability."}
