"""Okapi BM25 with postings and identical query/document tokenization."""

from collections import Counter, defaultdict
import math
import re

from ragbase.schema import RetrievalResult

STOP_WORDS = frozenset("a an the is are was were be been to of for in on at by and or as it i we you my our can do does did how what when which who must should much many".split())


def tokenize(text):
    return [token for token in re.findall(r"[^\W_]+(?:[-.][^\W_]+)*", text.casefold()) if token not in STOP_WORDS]


class BM25Retriever:
    def __init__(self, chunks, k1=1.5, b=0.75):
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("Invalid BM25 parameters")
        if len({chunk["chunk_id"] for chunk in chunks}) != len(chunks):
            raise ValueError("BM25 requires unique chunk identities")
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.postings = defaultdict(list)
        self.lengths = []
        for index, chunk in enumerate(chunks):
            tokens = tokenize(chunk["text"])
            self.lengths.append(len(tokens))
            for term, frequency in Counter(tokens).items():
                self.postings[term].append((index, frequency))
        self.average_length = sum(self.lengths) / max(len(chunks), 1) or 1

    def search(self, query, top_k):
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        scores = defaultdict(float)
        for term in set(tokenize(query)):
            postings = self.postings.get(term, [])
            idf = math.log(1 + (len(self.chunks) - len(postings) + 0.5) / (len(postings) + 0.5))
            for index, tf in postings:
                denominator = tf + self.k1 * (1 - self.b + self.b * self.lengths[index] / self.average_length)
                scores[index] += idf * tf * (self.k1 + 1) / denominator
        ranked = sorted(scores, key=lambda index: (-scores[index], self.chunks[index]["chunk_id"]))[:top_k]
        results = []
        for rank, index in enumerate(ranked, 1):
            chunk = self.chunks[index]
            metadata = dict(chunk.get("metadata", {}))
            results.append(RetrievalResult(chunk_id=chunk["chunk_id"], document_id=chunk.get("document_id", metadata.get("document_id", "")),
                                           score=float(scores[index]), rank=rank, text=chunk["text"], metadata=metadata,
                                           score_type="bm25", component_scores={"bm25": float(scores[index])}))
        return results
