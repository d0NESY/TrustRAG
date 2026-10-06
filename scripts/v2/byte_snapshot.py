"""Preserve V1 byte identity when a fresh clone changes text line endings."""

import argparse
import json
import os
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import sha256_file
from scripts.v2.common import EXPERIMENTS, REPORTS, ROOT, verify_v1

ARCHIVE = EXPERIMENTS / "v1_byte_snapshot.zip"
METADATA = REPORTS / "v1_byte_snapshot_manifest.json"


def create():
    manifest = verify_v1()
    if ARCHIVE.exists() or METADATA.exists():
        raise ValueError("Byte snapshot already exists; do not overwrite the frozen archive")
    files = {**manifest["files"], **manifest["core_algorithm_sha256"]}
    # Additional existing V1 records have remained unchanged in this branch.
    extra = [*sorted((ROOT / "docs").rglob("*")), *[ROOT / name for name in ["FINAL_REPORT.md", "README.md", "pyproject.toml", "poetry.lock"]]]
    for path in extra:
        if path.is_file():
            files[path.relative_to(ROOT).as_posix()] = sha256_file(path)
    with ZipFile(ARCHIVE, "w", compression=ZIP_DEFLATED) as archive:
        for name, digest in sorted(files.items()):
            path = ROOT / name
            if sha256_file(path) != digest:
                raise ValueError(f"Snapshot input changed: {name}")
            entry = ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            archive.writestr(entry, path.read_bytes())
    write_json(METADATA, {"original_workspace": str(ROOT), "files": files, "archive_sha256": sha256_file(ARCHIVE),
                         "purpose": "Exact frozen V1 bytes; new-clone line-ending recovery only; never overwrite original workspace."})
    verify_v1()
    print(f"Frozen V1 byte snapshot created without changing originals: {len(files)} files.")


def check_or_restore(restore=False):
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    if sha256_file(ARCHIVE) != metadata["archive_sha256"]:
        raise ValueError("Frozen byte archive checksum mismatch")
    mismatches = [name for name, digest in metadata["files"].items() if not (ROOT / name).is_file() or sha256_file(ROOT / name) != digest]
    if mismatches and not restore:
        raise ValueError(f"Frozen byte mismatches ({len(mismatches)}); inspect in a separate clone before restoring line endings")
    if mismatches:
        if os.path.normcase(str(ROOT.resolve())) == os.path.normcase(str(Path(metadata["original_workspace"]).resolve())):
            raise ValueError("Refusing to restore any file in the original frozen workspace")
        approved = []
        with ZipFile(ARCHIVE) as archive:
            for name in mismatches:
                target = (ROOT / name).resolve()
                if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
                    raise ValueError(f"Not an existing file within this clone: {name}")
                if target.suffix.lower() not in {".md", ".json", ".jsonl", ".py", ".yaml", ".yml", ".txt", ".csv", ".toml", ".lock", ".ps1", ".log"}:
                    raise ValueError(f"Refusing a binary-file mismatch: {name}")
                frozen = archive.read(name)
                if target.read_bytes().replace(b"\r\n", b"\n") != frozen.replace(b"\r\n", b"\n"):
                    raise ValueError(f"Semantic/binary modification detected; refusing restore: {name}")
                approved.append((target, frozen))
            # Validate every target before any write; restore only EOL variants.
            for target, frozen in approved:
                target.write_bytes(frozen)
    remaining = [name for name, digest in metadata["files"].items() if sha256_file(ROOT / name) != digest]
    if remaining:
        raise ValueError(f"Frozen bytes still differ: {remaining}")
    verify_v1()
    print(f"Frozen byte snapshot verified; EOL files restored: {len(mismatches)}.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--restore-line-endings", action="store_true")
    args = parser.parse_args()
    if args.create and args.restore_line_endings:
        parser.error("Creation and clone restoration are separate operations")
    create() if args.create else check_or_restore(args.restore_line_endings)


if __name__ == "__main__":
    main()
