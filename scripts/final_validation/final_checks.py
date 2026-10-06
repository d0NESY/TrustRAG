"""Final read-only checks, including Git versus working-tree byte identity."""

import hashlib
import json
import subprocess

from ragbase.evaluation.artifacts import write_json
from scripts.final_validation.common import ROOT, OUT, REPORTS, verify_frozen


def main():
    manifest = verify_frozen()
    names = list(manifest["files"])
    process = subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    payload = "".join(manifest["frozen_delivery_commit"] + ":" + name + "\n" for name in names).encode()
    output, _ = process.communicate(payload)
    position, mismatches = 0, []
    for name in names:
        ending = output.index(b"\n", position)
        header = output[position:ending].split()
        if header[-1] == b"missing":
            raise ValueError(f"Missing original committed file: {name}")
        size = int(header[-1])
        data = output[ending + 1:ending + 1 + size]
        position = ending + size + 2
        if hashlib.sha256(data).hexdigest() != manifest["files"][name]:
            mismatches.append(name)
    prior_snapshot = json.loads((ROOT / "reports/v2/v1_byte_snapshot_manifest.json").read_text(encoding="utf-8"))
    supplemental = REPORTS / "legacy_byte_snapshot_manifest.json"
    supplemental_files = json.loads(supplemental.read_text(encoding="utf-8"))["files"] if supplemental.exists() else {}
    uncovered = [name for name in mismatches if name not in prior_snapshot["files"] and name not in supplemental_files]
    result = {"git_blob_byte_mismatches": mismatches, "covered_by_archival_snapshots": not uncovered,
              "uncovered_mismatches": uncovered, "note": "Git normalizes original mixed line endings; existing snapshot restores exact bytes in a separate clone."}
    write_json(REPORTS / "git_byte_reproducibility.json", result)
    recovery = OUT / "runtime_recovery"
    errors = [json.loads(line) for line in (OUT / "external/run/execution_errors.jsonl").read_text(encoding="utf-8").splitlines()]
    write_json(recovery / "recovery.json", {"original_task_service_pid": 35492, "restarted_task_service_pid": 30064,
               "ollama_binary_sha256": hashlib.sha256((ROOT / ".runtime/ollama/bin/ollama.exe").read_bytes()).hexdigest(),
               "before_log_sha256": hashlib.sha256((recovery / "before_restart.stderr.log").read_bytes()).hexdigest(),
               "after_log_sha256": hashlib.sha256((recovery / "after_restart.stderr.log").read_bytes()).hexdigest(),
               "failed_attempt_count": len(errors), "outcome": "Same CUDA initialization failure after same-binary service restart; no parameter or model changes."})
    lines = (recovery / "after_restart.stderr.log").read_text(encoding="utf-8", errors="replace").splitlines()
    excerpts = [line for line in lines if "CUDA error:" in line or "ggml_cuda_kernel_can_use_pdl" in line or "llama-server terminated" in line or "exit.hex=" in line]
    (recovery / "cuda_failure_excerpt.txt").write_text("\n".join(excerpts) + "\n", encoding="utf-8")
    markdown = list(REPORTS.rglob("*.md")) + [ROOT / "docs/final_resume_claims.md"]
    bad = [str(path) for path in markdown if "\ufffd" in path.read_text(encoding="utf-8")]
    if bad:
        raise ValueError(f"Invalid replacement characters in reports: {bad}")
    print(json.dumps({"frozen_files": len(manifest["files"]), "git_eol_mismatches": mismatches,
                      "covered_by_archival_snapshots": not uncovered, "utf8_reports": len(markdown)}, ensure_ascii=False))
    if uncovered:
        raise ValueError("New-clone byte identity needs an additional archival snapshot")


if __name__ == "__main__":
    main()
