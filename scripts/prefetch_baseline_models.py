"""Download and verify the unchanged upstream embedding/reranker models."""

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["FASTEMBED_CACHE_PATH"] = str(ROOT / ".runtime" / "fastembed")

from flashrank import Ranker

defaults = list(Ranker.__init__.__defaults__)
defaults[1] = str(ROOT / ".runtime" / "flashrank")
Ranker.__init__.__defaults__ = tuple(defaults)

from ragbase.model import create_embeddings, create_reranker
from langchain_core.documents import Document

embedding = create_embeddings()
print("Embedding verified; dimensions:", len(embedding.embed_query("paid sick leave")), flush=True)
reranker = create_reranker()
result = reranker.compress_documents([Document(page_content="Employees have ten paid sick days.")], "How much sick leave?")
print("Reranker verified:", result[0].metadata, flush=True)
