"""Existing frozen V2 evaluator, directed only into a separate new run path."""

import argparse
import sys

from scripts.release.common import ROOT, begin


def safe_output(value):
    path = (ROOT / value).resolve()
    base = (ROOT / "experiments/reproduction").resolve()
    if not path.is_relative_to(base) or path == base:
        raise ValueError("Use a named new child under experiments/reproduction; never formal directories")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--phase", choices=["retrieval", "gate", "all"], default="all")
    args = parser.parse_args()
    begin()
    path = safe_output(args.output_root)
    path.mkdir(parents=True, exist_ok=True)
    import scripts.v2.evaluate as original
    original.EXPERIMENTS = path
    sys.argv = [sys.argv[0], "--phase", args.phase, "--split", "both"]
    original.main()


if __name__ == "__main__":
    main()
