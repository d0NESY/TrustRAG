"""New-clone exact-byte restoration, preserving explicitly revised README."""

import argparse
import json
import os
from pathlib import Path
from zipfile import ZipFile

from ragbase.evaluation.benchmark import sha256_file
from scripts.release.common import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    snapshots = [(ROOT / "experiments/v2/v1_byte_snapshot.zip", ROOT / "reports/v2/v1_byte_snapshot_manifest.json"),
                 (ROOT / "experiments/final_validation/legacy_byte_snapshot.zip", ROOT / "reports/final_validation/legacy_byte_snapshot_manifest.json")]
    approved = []
    for archive_path, metadata_path in snapshots:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if sha256_file(archive_path) != metadata["archive_sha256"]:
            raise ValueError("Frozen byte archive changed")
        with ZipFile(archive_path) as archive:
            for name, digest in metadata["files"].items():
                if name == "README.md":
                    continue  # Explicitly revised by this release request; keep it.
                path = (ROOT / name).resolve()
                if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                    raise ValueError(f"Invalid restoration target: {name}")
                if sha256_file(path) == digest:
                    continue
                if not args.restore:
                    raise ValueError(f"Frozen byte mismatch: {name}; use a separate clone for restoration")
                if os.path.normcase(str(ROOT.resolve())) == os.path.normcase(str(Path(metadata["original_workspace"]).resolve())):
                    raise ValueError("Refusing writes to original frozen workspace")
                frozen = archive.read(name)
                if path.read_bytes().replace(b"\r\n", b"\n") != frozen.replace(b"\r\n", b"\n"):
                    raise ValueError(f"Semantic modification, not line endings: {name}")
                approved.append((path, frozen))
    for path, data in approved:
        path.write_bytes(data)
    print(f"Release byte check complete; {len(approved)} EOL-only clone files restored; revised README retained.")


if __name__ == "__main__":
    main()
