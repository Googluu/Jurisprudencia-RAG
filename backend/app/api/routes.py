"""FastAPI routes."""

from __future__ import annotations

import logging
import time

import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types

from app.api.rag import stream_rag_response
from app.api.schemas import ObservabilityResult, QueryRequest, SourceDocument
from app.config import settings
from app.search.hybrid import hybrid_search
from app.search.lexical import lexical_search
from app.search.semantic import semantic_search
from app.store import store

router = APIRouter()
logger = logging.getLogger(__name__)


def _embed_query(question: str) -> np.ndarray:
    """Embed a query string using Gemini."""
    if not settings.google_api_key:
        raise HTTPException(status_code=503, detail="GOOGLE_API_KEY not configured.")
    client = genai.Client(api_key=settings.google_api_key)
    response = client.models.embed_content(
        model=settings.embedding_model,
        contents=[question],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return np.array(response.embeddings[0].values, dtype=np.float32)


@router.post(
    "/chat/stream",
    summary="RAG chat with SSE streaming",
    description=(
        "Sends a question to the RAG pipeline. "
        "Response is streamed as Server-Sent Events. "
        "Events: `text` (incremental answer), `sources` (final sources + metadata), `error`."
    ),
)
async def chat_stream(request: QueryRequest):
    if not store.ready:
        raise HTTPException(status_code=503, detail="Index not loaded. Run the ingestion pipeline first.")

    retrieval_start = time.monotonic()
    try:
        query_vec = _embed_query(request.question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Embedding error: {exc}") from exc

    results = hybrid_search(
        query=request.question,
        query_vec=query_vec,
        doc_matrix=store.embeddings,
        bm25=store.bm25,
        df=store.df,
        top_k=request.top_k,
        rrf_k=settings.rrf_k,
    )
    retrieval_ms = (time.monotonic() - retrieval_start) * 1000
    logger.info("Retrieval: %d results in %.1f ms", len(results), retrieval_ms)

    return StreamingResponse(
        stream_rag_response(request.question, results),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/debug/retrieval",
    response_model=ObservabilityResult,
    summary="Observability: full retrieval detail",
    description=(
        "Returns the complete retrieval breakdown for a question: "
        "individual semantic and lexical scores, fused ranking, and timing per stage."
    ),
)
async def debug_retrieval(request: QueryRequest):
    if not store.ready:
        raise HTTPException(status_code=503, detail="Index not loaded.")

    start = time.monotonic()
    query_vec = _embed_query(request.question)

    candidate_pool = min(50, len(store.df))
    sem_hits = semantic_search(query_vec, store.embeddings, top_k=candidate_pool)
    lex_hits = lexical_search(request.question, store.bm25, top_k=candidate_pool)

    results = hybrid_search(
        query=request.question,
        query_vec=query_vec,
        doc_matrix=store.embeddings,
        bm25=store.bm25,
        df=store.df,
        top_k=request.top_k,
        rrf_k=settings.rrf_k,
    )
    retrieval_ms = (time.monotonic() - start) * 1000

    def _hit_detail(hits: list[tuple[int, float]], label: str) -> list[dict]:
        out = []
        for rank, (idx, score) in enumerate(hits[:20]):
            row = store.df.iloc[idx]
            out.append({
                "rank": rank + 1,
                "chunk_index": int(row["chunk_index"]),
                "doc_id": str(row["doc_id"]),
                "section_type": str(row["section_type"]),
                "section_name": str(row["section_name"]),
                f"{label}_score": round(score, 4),
                "text_preview": str(row["chunk_text"])[:120],
            })
        return out

    return ObservabilityResult(
        question=request.question,
        retrieval_time_ms=round(retrieval_ms, 1),
        semantic_hits=_hit_detail(sem_hits, "semantic"),
        lexical_hits=_hit_detail(lex_hits, "lexical"),
        fused_results=[
            SourceDocument(
                doc_id=r.doc_id,
                source_file=r.source_file,
                section_type=r.section_type,
                section_name=r.section_name,
                chunk_text=r.chunk_text,
                semantic_score=r.semantic_score,
                lexical_score=r.lexical_score,
                rrf_score=r.rrf_score,
            )
            for r in results
        ],
    )


@router.get("/health", summary="Health check")
async def health():
    return {
        "status": "ok" if store.ready else "not_ready",
        "chunks_loaded": len(store.df) if store.ready else 0,
        "embeddings_shape": list(store.embeddings.shape) if store.ready else [],
    }
