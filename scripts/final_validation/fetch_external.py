"""Download an existing public human-annotated dataset; never invent gold."""

import json
import requests

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import sha256_file
from scripts.final_validation.common import OUT, REPORTS, prepare


def main():
    prepare()
    directory = OUT / "external"
    directory.mkdir(exist_ok=True)
    target = directory / "squad_v2_dev.json"
    provenance = directory / "download_provenance.json"
    if target.exists():
        saved = json.loads(provenance.read_text(encoding="utf-8"))
        if sha256_file(target) != saved["sha256"]:
            raise ValueError("External source changed")
        print("Public SQuAD2 source already downloaded and unchanged.")
        return
    attempts = []
    for url in ["https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json",
                "https://raw.githubusercontent.com/rajpurkar/SQuAD-explorer/master/dataset/dev-v2.0.json"]:
        try:
            response = requests.get(url, timeout=(10, 25))
            response.raise_for_status()
            data = response.json()
            assert data["version"] == "v2.0" and data["data"]
            target.write_bytes(response.content)
            write_json(provenance, {"status": "downloaded", "url": url, "sha256": sha256_file(target), "bytes": len(response.content),
                       "article_count": len(data["data"]), "source": "Public SQuAD2 development set; natural Wikipedia excerpts and native crowd QA/gold",
                       "prior_attempts": attempts, "gold_generated_by_evaluated_model": False})
            print(f"Public external source downloaded: {len(response.content)} bytes, {len(data['data'])} articles.")
            return
        except (requests.RequestException, ValueError, AssertionError) as error:
            attempts.append({"url": url, "error": str(error)})
    write_json(provenance, {"status": "blocked", "attempts": attempts})
    (REPORTS / "EXTERNAL_TEST_BLOCKED.md").write_text("# External Test：BLOCKED\n\n已尝试公开 SQuAD2 官方数据源与 GitHub 镜像，但当前环境无法获取来源。未创建模拟 PDF 或伪造自然 QA。\n\n" + json.dumps(attempts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("External source retrieval blocked; reasons recorded, no invented data.")


if __name__ == "__main__":
    main()
