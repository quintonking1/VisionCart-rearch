"""The search tool workers call: hybrid BM25 + embedding retrieval within one category."""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

from visioncart.catalog.store import Catalog
from visioncart.vision import search_text

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs = [Counter(d) for d in docs]
        self.lens = [len(d) for d in docs]
        self.avg = sum(self.lens) / max(len(docs), 1)
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query: list[str]) -> np.ndarray:
        out = np.zeros(len(self.docs), dtype=np.float32)
        for i, (tf, length) in enumerate(zip(self.docs, self.lens)):
            for t in query:
                if t in tf:
                    f = tf[t]
                    out[i] += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg))
        return out


class CatalogSearch:
    def __init__(self, catalog: Catalog, bm25_weight: float = 0.4):
        self.catalog = catalog
        self.bm25 = BM25([tokenize(search_text(p.name, p.category, p.attributes)) for p in catalog.products])
        self.bm25_weight = bm25_weight

    def search(self, query: str, query_vec: np.ndarray, category: str, k: int = 10,
               exclude: set[str] = frozenset()) -> list[tuple[str, float]]:
        mask = np.array([p.category == category and p.id not in exclude for p in self.catalog.products])
        if not mask.any():
            return []
        lexical = self.bm25.scores(tokenize(query))
        top = lexical[mask].max()
        lexical = lexical / top if top > 0 else lexical
        dense = self.catalog.search_vecs @ query_vec
        score = self.bm25_weight * lexical + (1 - self.bm25_weight) * dense
        idx = [i for i in np.argsort(-score) if mask[i]][:k]
        return [(self.catalog.products[i].id, float(score[i])) for i in idx]
