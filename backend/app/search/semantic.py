"""Semantic search via cosine similarity over Gemini embeddings."""

from __future__ import annotations

import numpy as np


def cosine_similarity_matrix(query_vec: np.ndarray, doc_matrix: np.ndarray) -> np.ndarray:
    """Return cosine similarity between query_vec and every row in doc_matrix."""
    q = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    norms = np.linalg.norm(doc_matrix, axis=1, keepdims=True) + 1e-10
    normed = doc_matrix / norms
    return (normed @ q).astype(float)


def semantic_search(
    query_vec: np.ndarray,
    doc_matrix: np.ndarray,
    top_k: int,
) -> list[tuple[int, float]]:
    """
    Return [(index, score), ...] sorted by descending cosine similarity.
    top_k results are returned.
    """
    scores = cosine_similarity_matrix(query_vec, doc_matrix)
    top_indices = np.argpartition(scores, -min(top_k, len(scores)))[-top_k:]
    top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
    return [(int(i), float(scores[i])) for i in top_indices]
