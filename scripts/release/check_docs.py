"""UTF-8 and local reading-entry links, without changing documents."""

import json
import re

from scripts.release.common import ROOT, RELEASE, verify
from ragbase.evaluation.artifacts import write_json


def main():
    paths = [ROOT / name for name in ["README.md", "FINAL_PROJECT_REPORT.md", "REPRODUCE.md", "docs/final_resume_claims.md",
                                     "docs/final_resume_claims_engineering.md", "docs/project_pitch.md", "docs/project_defense_qa.md"]]
    broken, encoding = [], []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if "\ufffd" in text:
            encoding.append(path.relative_to(ROOT).as_posix())
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if not target.startswith(("http:", "https:", "#")) and not (path.parent / target.split("#")[0]).exists():
                broken.append({"source": path.relative_to(ROOT).as_posix(), "target": target})
    if encoding or broken:
        raise ValueError(f"Documentation checks failed: {encoding}, {broken}")
    data = verify()
    result = {"utf8_documents": len(paths), "broken_links": broken, "replacement_characters": encoding,
              "frozen_files_verified": len(data["entries"]) - len(data["allowed_updates"])}
    write_json(RELEASE / "documentation_checks.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
