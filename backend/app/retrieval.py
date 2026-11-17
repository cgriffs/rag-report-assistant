"""Retrieval layer: a local TF-IDF index with cosine similarity.

Why TF-IDF by default: it runs anywhere with no model downloads and no API
key, which keeps the demo and the test suite deterministic and fast. The
index stores sparse term vectors, so swapping in a dense embedding model
(for example Azure OpenAI embeddings) only changes how vectors are built,
not the search interface. The DocumentIndex class is that interface.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from .chunking import Chunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Function words carry no topical signal and would otherwise let unrelated
# questions match every chunk that contains "the".
_STOPWORDS = frozenset(
    "a an the and or of to in on for with by at from as is are was were be "
    "been it its this that these those what which who whom when where why "
    "how much many do does did can could will would should may might i you "
    "he she we they them his her their our your my me him us am an".split()
)


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if token not in _STOPWORDS
    ]


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float


@dataclass
class DocumentIndex:
    chunks: list[Chunk] = field(default_factory=list)
    _idf: dict[str, float] = field(default_factory=dict)
    _vectors: list[dict[str, float]] = field(default_factory=list)

    def add(self, new_chunks: list[Chunk]) -> None:
        self.chunks.extend(new_chunks)
        self._rebuild()

    def _rebuild(self) -> None:
        doc_freq: Counter[str] = Counter()
        per_chunk_counts: list[Counter[str]] = []
        for chunk in self.chunks:
            counts = Counter(tokenize(chunk.text))
            per_chunk_counts.append(counts)
            for term in counts:
                doc_freq[term] += 1
        n = max(len(self.chunks), 1)
        self._idf = {
            term: math.log((1 + n) / (1 + df)) + 1.0
            for term, df in doc_freq.items()
        }
        self._vectors = [
            self._vectorize(counts) for counts in per_chunk_counts
        ]

    def _vectorize(self, counts: Counter[str]) -> dict[str, float]:
        total = sum(counts.values()) or 1
        return {
            term: (count / total) * self._idf.get(term, 1.0)
            for term, count in counts.items()
        }

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(value * b.get(term, 0.0) for term, value in a.items())
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: str, top_k: int = 4) -> list[ScoredChunk]:
        if not self.chunks:
            return []
        query_vector = self._vectorize(Counter(tokenize(query)))
        scored = [
            ScoredChunk(chunk=chunk, score=self._cosine(query_vector, vector))
            for chunk, vector in zip(self.chunks, self._vectors)
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return [item for item in scored[:top_k] if item.score > 0.0]
