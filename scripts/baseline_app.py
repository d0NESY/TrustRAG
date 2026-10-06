"""Run the unchanged upstream app using its supported local-model configuration."""

from pathlib import Path
import os
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_ROOT = ROOT / ".runtime" / "upstream"
if not (UPSTREAM_ROOT / "app.py").exists():
    raise RuntimeError("Run python scripts/export_upstream.py before baseline reproduction")
sys.path.insert(0, str(UPSTREAM_ROOT))
os.environ["FASTEMBED_CACHE_PATH"] = str(ROOT / ".runtime" / "fastembed")

# FlashRank 0.2.8 hardcodes /tmp. Change only the cache location; the model,
# ranking algorithm and upstream compressor's top_n=3 are unchanged.
from flashrank import Ranker

defaults = list(Ranker.__init__.__defaults__)
defaults[1] = str(ROOT / ".runtime" / "flashrank")
Ranker.__init__.__defaults__ = tuple(defaults)

from ragbase.config import Config

Config.Model.USE_LOCAL = True
Config.Path.APP_HOME = ROOT / ".runtime" / "baseline"
Config.Path.DATABASE_DIR = Config.Path.APP_HOME / "docs-db"
Config.Path.DOCUMENTS_DIR = Config.Path.APP_HOME / "tmp"
Config.Path.IMAGES_DIR = UPSTREAM_ROOT / "images"

runpy.run_path(str(UPSTREAM_ROOT / "app.py"), run_name="__main__")
