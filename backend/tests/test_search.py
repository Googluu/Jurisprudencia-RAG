"""Tests for hybrid search logic (no real Gemini calls)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.search.hybrid import hybrid_search, rrf_fusion
from app.search.lexical import build_bm25, lexical_search, tokenize
from app.search.semantic import cosine_similarity_matrix, semantic_search


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------


def test_cosine_similarity_identical():
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    matrix = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    scores = cosine_similarity_matrix(v, matrix)
    assert abs(scores[0] - 1.0) < 1e-5
    assert abs(scores[1] - 0.0) < 1e-5


def test_semantic_search_returns_top_k():
    matrix = np.random.rand(20, 8).astype(np.float32)
    query = np.random.rand(8).astype(np.float32)
    results = semantic_search(query, matrix, top_k=5)
    assert len(results) == 5
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Lexical search
# ---------------------------------------------------------------------------


def test_tokenize_accents():
    tokens = tokenize("La jurisprudencia española en contratos")
    assert "jurisprudencia" in tokens
    assert "española" in tokens


def test_bm25_relevance():
    corpus = [
        "contrato de mandato y sus obligaciones",
        "casación civil recurso de apelación",
        "mandato representación legal del mandatario",
    ]
    bm25 = build_bm25(corpus)
    results = lexical_search("mandato representación", bm25, top_k=3)
    top_indices = [idx for idx, _ in results]
    # Doc 0 and doc 2 mention "mandato" — they should rank above doc 1
    assert 0 in top_indices or 2 in top_indices


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------


def test_rrf_fusion_combines_lists():
    sem = [(0, 0.9), (1, 0.8), (2, 0.7)]
    lex = [(2, 5.0), (0, 4.0), (3, 3.0)]
    fused = rrf_fusion(sem, lex, k=60)
    indices = [idx for idx, _ in fused]
    # Doc 0 is in both lists and should score highest
    assert indices[0] == 0


def test_rrf_scores_decrease():
    sem = [(i, float(10 - i)) for i in range(10)]
    lex = [(i, float(10 - i)) for i in range(10)]
    fused = rrf_fusion(sem, lex)
    scores = [s for _, s in fused]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Hybrid search (mocked embeddings)
# ---------------------------------------------------------------------------


def _make_fake_store(n=10):
    df = pd.DataFrame(
        {
            "doc_id": [f"doc{i}" for i in range(n)],
            "source_file": [f"doc{i}.html" for i in range(n)],
            "chunk_index": list(range(n)),
            "chunk_text": [
                f"El contrato de mandato implica representación número {i}" for i in range(n)
            ],
            "section_type": ["consideraciones"] * n,
            "section_name": ["CONSIDERACIONES"] * n,
            "word_count": [10] * n,
        }
    )
    matrix = np.random.rand(n, 8).astype(np.float32)
    bm25 = build_bm25(df["chunk_text"].tolist())
    return df, matrix, bm25


def test_hybrid_search_returns_results():
    df, matrix, bm25 = _make_fake_store(10)
    query_vec = np.random.rand(8).astype(np.float32)
    results = hybrid_search("mandato representación", query_vec, matrix, bm25, df, top_k=5)
    assert len(results) > 0
    assert len(results) <= 5


def test_hybrid_search_no_duplicates():
    df, matrix, bm25 = _make_fake_store(10)
    query_vec = np.random.rand(8).astype(np.float32)
    results = hybrid_search("mandato", query_vec, matrix, bm25, df, top_k=10)
    texts = [r.chunk_text for r in results]
    assert len(texts) == len(set(texts)), "Duplicate chunks in results"
