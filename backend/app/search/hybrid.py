"""
Hybrid search: semantic + BM25 fused with Reciprocal Rank Fusion (RRF).

RRF score = Σ 1 / (k + rank_i)
where k=60 is the standard constant that dampens the influence of top-ranked
results and makes the fusion robust to score scale differences between the two
retrieval methods.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from app.search.lexical import lexical_search
from app.search.semantic import semantic_search


@dataclass
class SearchResult:
    chunk_index: int
    doc_id: str
    source_file: str
    section_type: str
    section_name: str
    chunk_text: str
    semantic_score: float
    lexical_score: float
    rrf_score: float


def rrf_fusion(
    semantic_hits: list[tuple[int, float]],
    lexical_hits: list[tuple[int, float]],
    k: int = 60,
) -> list[tuple[int, float]]:
    """
    Merge two ranked lists into a single RRF-ranked list.
    Returns [(index, rrf_score)] sorted descending.
    """
    scores: dict[int, float] = {}

    for rank, (idx, _) in enumerate(semantic_hits):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)

    for rank, (idx, _) in enumerate(lexical_hits):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def hybrid_search(
    query: str,
    query_vec: np.ndarray,
    doc_matrix: np.ndarray,
    bm25: BM25Okapi,
    df: pd.DataFrame,
    top_k: int = 8,
    rrf_k: int = 60,
    candidate_pool: int = 50,
) -> list[SearchResult]:
    """
    Run hybrid retrieval and return top_k deduplicated results.

    candidate_pool: how many hits to request from each retriever before fusion.
    Larger pool increases recall at the cost of more candidates to fuse.
    """
    sem_hits = semantic_search(query_vec, doc_matrix, top_k=candidate_pool)
    lex_hits = lexical_search(query, bm25, top_k=candidate_pool)

    # Build score lookup for annotation
    sem_scores: dict[int, float] = dict(sem_hits)
    lex_scores: dict[int, float] = dict(lex_hits)

    fused = rrf_fusion(sem_hits, lex_hits, k=rrf_k)

    results: list[SearchResult] = []
    seen_texts: set[str] = set()

    for idx, rrf_score in fused[:top_k]:
        row = df.iloc[idx]
        text = str(row["chunk_text"])
        # Deduplicate by exact text match (avoids duplicate chunks from same doc)
        if text in seen_texts:
            continue
        seen_texts.add(text)

        results.append(
            SearchResult(
                chunk_index=int(row["chunk_index"]),
                doc_id=str(row["doc_id"]),
                source_file=str(row["source_file"]),
                section_type=str(row["section_type"]),
                section_name=str(row["section_name"]),
                chunk_text=text,
                semantic_score=sem_scores.get(idx, 0.0),
                lexical_score=lex_scores.get(idx, 0.0),
                rrf_score=rrf_score,
            )
        )

    return results
