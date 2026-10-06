"""Export the recorded upstream commit without changing the working checkout."""

import io
from pathlib import Path
import subprocess
import zipfile

UPSTREAM_COMMIT = "5af7b79162329fa0b725b39d1aeeea7eb1e4428b"
ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = (ROOT / ".runtime" / "upstream").resolve()
    destination.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(["git", "archive", "--format=zip", UPSTREAM_COMMIT], cwd=ROOT, check=True, capture_output=True).stdout
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        for member in package.infolist():
            if not (destination / member.filename).resolve().is_relative_to(destination):
                raise ValueError("Archive member escapes upstream snapshot")
        package.extractall(destination)
    (ROOT / ".runtime" / "upstream-commit.txt").write_text(UPSTREAM_COMMIT + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
