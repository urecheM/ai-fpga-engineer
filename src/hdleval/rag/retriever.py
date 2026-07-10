"""A dependency-free lexical retriever over a small knowledge corpus.

Retrieves vendor documentation, synthesis guidelines, protocol specs and
benchmark exemplars by TF-style term overlap. It is intentionally simple and
embedding-free so it runs anywhere; a vector-DB retriever can replace it behind
the same interface.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    source: str = ""


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


class KnowledgeRetriever:
    def __init__(self, docs: list[Document]) -> None:
        self.docs = docs
        self._tok = [Counter(_tokens(d.text)) for d in docs]
        df: Counter[str] = Counter()
        for c in self._tok:
            df.update(c.keys())
        n = max(1, len(docs))
        self._idf = {t: math.log(1 + n / (1 + f)) for t, f in df.items()}

    def retrieve(self, query: str, k: int = 3) -> list[Document]:
        q = Counter(_tokens(query))
        scored: list[tuple[float, Document]] = []
        for doc, tf in zip(self.docs, self._tok):
            score = sum(q[t] * tf.get(t, 0) * self._idf.get(t, 0.0) for t in q)
            scored.append((score, doc))
        scored.sort(key=lambda x: -x[0])
        return [d for s, d in scored[:k] if s > 0]
