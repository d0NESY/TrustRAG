from dataclasses import replace

import yaml

from ragbase.config import load_config
from scripts.v2.common import ROOT, verify_v1


def main():
    verify_v1()
    for folder in [ROOT / "configs/demo", ROOT / "configs/v2"]:
        folder.mkdir(exist_ok=True)
    mapping = [("dense", "baseline"), ("bm25", "bm25"), ("dense_reranker", "dense_reranker"), ("hybrid", "hybrid"), ("hybrid_reranker", "hybrid_reranker")]
    for name, original in mapping:
        config = load_config(ROOT / "configs" / (original + ".yaml"))
        disabled = replace(config, answerability=replace(config.answerability, enabled=False))
        demo_path = ROOT / "configs/demo" / (original + ".yaml")
        demo_path.write_text("# V1 independent test showed no FAR improvement and increased false refusal.\n# Gate is experimental/optional; the V1 experiment config is preserved separately.\n" + yaml.safe_dump(disabled.to_dict(), sort_keys=False), encoding="utf-8", newline="\n")
        v2_path = ROOT / "configs/v2" / (name + ".yaml")
        v2_path.write_text("# Frozen V1 algorithm parameters; no V2 test tuning.\n" + yaml.safe_dump(disabled.to_dict(), sort_keys=False), encoding="utf-8", newline="\n")
    current = load_config(ROOT / "configs/hybrid_reranker.yaml")
    gate = replace(current, name="current_gate_v2")
    (ROOT / "configs/v2/current_gate.yaml").write_text("# G1: exactly the V1 hybrid-reranker threshold; no V2 recalibration.\n" + yaml.safe_dump(gate.to_dict(), sort_keys=False), encoding="utf-8", newline="\n")
    verify_v1()
    print("Created V2 frozen configs and gate-off demo configs; V1 configs unchanged.")


if __name__ == "__main__":
    main()
