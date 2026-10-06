"""Supplement existing V1 snapshot with five unchanged legacy source files."""

import argparse
import json
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import sha256_file
from scripts.final_validation.common import ROOT, OUT, REPORTS, verify_frozen

ARCHIVE = OUT / "legacy_byte_snapshot.zip"
METADATA = REPORTS / "legacy_byte_snapshot_manifest.json"


def create():
    verify_frozen()
    if ARCHIVE.exists() or METADATA.exists():
        raise ValueError("Supplement already exists; preserve it")
    info = json.loads((REPORTS / "git_byte_reproducibility.json").read_text(encoding="utf-8"))
    names = info["uncovered_mismatches"]
    expected = {"ragbase/chain.py", "ragbase/ingestor.py", "ragbase/retriever.py", "ragbase/session_history.py", "ragbase/uploader.py"}
    if set(names) != expected:
        raise ValueError("Unexpected source differences; do not broaden restoration automatically")
    with ZipFile(ARCHIVE, "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(names):
            entry = ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            archive.writestr(entry, (ROOT / name).read_bytes())
    write_json(METADATA, {"original_workspace": str(ROOT), "files": {name: sha256_file(ROOT / name) for name in names},
                         "archive_sha256": sha256_file(ARCHIVE), "purpose": "Unchanged legacy V1 code exact-byte backup; EOL-only restoration in a separate clone."})
    print("Five untouched legacy source files archived without modifying originals.")


def check(restore=False):
    import scripts.v2.byte_snapshot as original
    archive, metadata = original.ARCHIVE, original.METADATA
    try:
        original.ARCHIVE, original.METADATA = ARCHIVE, METADATA
        original.check_or_restore(restore)
    finally:
        original.ARCHIVE, original.METADATA = archive, metadata
    verify_frozen()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--restore-line-endings", action="store_true")
    args = parser.parse_args()
    if args.create and args.restore_line_endings:
        parser.error("Do not combine archive creation and clone restoration")
    create() if args.create else check(args.restore_line_endings)


if __name__ == "__main__":
    main()
