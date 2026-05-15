"""Lexical search via BM25 (rank-bm25)."""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    """Lowercase + split on non-alphanumeric (keeps accented chars)."""
    return re.findall(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ0-9]+", text.lower())


def build_bm25(corpus: list[str]) -> BM25Okapi:
    tokenized = [tokenize(doc) for doc in corpus]
    return BM25Okapi(tokenized)


def lexical_search(
    query: str,
    bm25: BM25Okapi,
    top_k: int,
) -> list[tuple[int, float]]:
    """Return [(index, score), ...] sorted by descending BM25 score."""
    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)

    import numpy as np

    top_indices = (-scores).argsort()[:top_k]
    return [(int(i), float(scores[i])) for i in top_indices if scores[i] > 0]
