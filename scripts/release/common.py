"""Release-only documentation updates; frozen inputs remain byte-identical."""

from datetime import datetime
import json
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import sha256_file
from scripts.final_validation.common import verify_frozen

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "reports/release"
AUTHORIZED_DOCS = {"README.md", "docs/final_resume_claims.md"}


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()


def begin():
    RELEASE.mkdir(exist_ok=True)
    path = RELEASE / "release_input_manifest.json"
    if not path.exists():
        verify_frozen()
        validation = json.loads((ROOT / "reports/final_validation/artifact_verification.json").read_text(encoding="utf-8"))
        for key in ["validation_files_sha256", "driver_sha256"]:
            changed = [name for name, digest in validation[key].items() if sha256_file(ROOT / name) != digest]
            if changed:
                raise ValueError(f"Previously frozen validation inputs changed: {changed}")
        files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
        entries = {name: {"size": (ROOT / name).stat().st_size, "sha256": sha256_file(ROOT / name),
                          "authorized_documentation_update": name in AUTHORIZED_DOCS}
                   for name in files if name and (ROOT / name).is_file()}
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        write_json(path, {"baseline_head": head, "timestamp": now(), "entries": entries,
                         "allowed_updates": sorted(AUTHORIZED_DOCS), "rule": "Only explicitly requested README/resume revisions; all formal artifacts immutable."})
    return verify()


def verify():
    data = json.loads((RELEASE / "release_input_manifest.json").read_text(encoding="utf-8"))
    changed = [name for name, entry in data["entries"].items() if name not in AUTHORIZED_DOCS and
               (not (ROOT / name).is_file() or sha256_file(ROOT / name) != entry["sha256"])]
    if changed:
        raise ValueError(f"Frozen release inputs changed; STOP: {changed}")
    verify_frozen()
    return data


def write_md(path, text):
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    data = begin()
    print(f"Release baseline {data['baseline_head']}; {len(data['entries'])} existing files verified.")
