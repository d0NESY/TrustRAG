"""Download a pinned official portable Ollama release into the project runtime."""

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="0.35.1")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / ".runtime" / "ollama"
    root.mkdir(parents=True, exist_ok=True)
    url = f"https://api.github.com/repos/ollama/ollama/releases/tags/v{args.version}"
    with urllib.request.urlopen(url, timeout=60) as response:
        release = json.load(response)
    asset = next(a for a in release["assets"] if a["name"] == "ollama-windows-amd64.zip")
    (root / "release.json").write_text(json.dumps(asset, indent=2), encoding="utf-8")
    archive = root / asset["name"]
    if not archive.exists() or archive.stat().st_size != asset["size"]:
        print(f"Downloading Ollama {args.version}: {asset['size'] / 2**20:.0f} MiB", flush=True)
        with urllib.request.urlopen(asset["browser_download_url"], timeout=120) as response, archive.open("wb") as output:
            received = 0
            next_report = 64 * 2**20
            while block := response.read(2**20):
                output.write(block)
                received += len(block)
                if received >= next_report:
                    print(f"Downloaded {received / 2**20:.0f} MiB", flush=True)
                    next_report += 64 * 2**20
    if archive.stat().st_size != asset["size"]:
        raise RuntimeError("Incomplete download")
    expected_digest = asset.get("digest")
    if expected_digest:
        with archive.open("rb") as source:
            actual = "sha256:" + hashlib.file_digest(source, "sha256").hexdigest()
        if actual != expected_digest:
            raise RuntimeError("Official release checksum mismatch")
    destination = (root / "bin").resolve()
    destination.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            if not (destination / member.filename).resolve().is_relative_to(destination):
                raise ValueError("Archive member escapes destination")
        package.extractall(destination)
    print(f"Installed portable binary: {destination / 'ollama.exe'}", flush=True)


if __name__ == "__main__":
    main()
