"""Pull a real Ollama model, logging bounded progress and its resolved digest."""

import argparse
import json
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gemma2:9b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    last = None
    with requests.post(args.base_url + "/api/pull", json={"name": args.model, "stream": True}, stream=True, timeout=(30, 300)) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            event = json.loads(line)
            if "error" in event:
                raise RuntimeError(event["error"])
            percent = int(100 * event.get("completed", 0) / max(event.get("total", 1), 1))
            current = (event.get("status"), percent // 5)
            if current != last:
                print(json.dumps({"status": current[0], "percent": percent}), flush=True)
                last = current
    tags = requests.get(args.base_url + "/api/tags", timeout=30).json()
    resolved = next(model for model in tags["models"] if model["name"] == args.model)
    output = Path(__file__).resolve().parents[1] / ".runtime" / "ollama" / "model.json"
    output.write_text(json.dumps(resolved, indent=2), encoding="utf-8")
    print("Resolved model:", resolved["name"], resolved["digest"], flush=True)


if __name__ == "__main__":
    main()
