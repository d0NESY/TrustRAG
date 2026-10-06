import argparse
from pathlib import Path

from ragbase.config import load_config
from ragbase.ingestion.indexer import build_index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/hybrid_reranker.yaml")
    parser.add_argument("--documents", default="data/documents")
    args = parser.parse_args()
    index = build_index(Path(args.documents).glob("*.pdf"), load_config(args.config))
    print(f"Index {index.manifest['index_id']}: {index.manifest['chunk_count']} chunks / {index.manifest['page_count']} pages")
    print(index.path)
    index.close()


if __name__ == "__main__":
    main()
