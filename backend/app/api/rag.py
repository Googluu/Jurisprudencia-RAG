"""
RAG generation layer: builds prompt, calls Gemini with streaming,
yields SSE-formatted events.
"""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator

from google import genai
from google.genai import types

from app.config import settings
from app.search.hybrid import SearchResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Eres un asistente jurídico experto en jurisprudencia de la Corte Suprema de Justicia \
de Colombia, Sala de Casación Civil. Tu función es responder preguntas basándote en \
los fragmentos de sentencias que se te proporcionan como contexto.

Reglas:
1. Usa TODA la información disponible en los fragmentos para construir una respuesta \
   completa. Si el tema aparece de forma indirecta o relacionada, incorpóralo.
2. Cita siempre el documento y la sección de donde proviene cada afirmación. \
   Formato: "según la sección de [nombre_sección] de la sentencia [doc_id]…"
3. Si los fragmentos son parcialmente relevantes, responde con lo que tienes y aclara \
   al final qué aspectos no están cubiertos en el corpus disponible.
4. Solo indica que no tienes información si los fragmentos son completamente irrelevantes \
   para la pregunta (ningún fragmento guarda relación temática alguna).
5. No inventes información que no esté en los fragmentos, pero sí puedes sintetizar, \
   relacionar y organizar el contenido de distintas fuentes.
6. Responde en español con lenguaje jurídico preciso pero comprensible.
"""


def _build_context_block(results: list[SearchResult]) -> str:
    parts: list[str] = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[Fuente {i}]\n"
            f"Documento: {r.doc_id}\n"
            f"Archivo: {r.source_file}\n"
            f"Sección tipo: {r.section_type}\n"
            f"Sección nombre: {r.section_name}\n"
            f"Texto:\n{r.chunk_text}\n"
        )
    return "\n---\n".join(parts)


def _build_user_message(question: str, context: str) -> str:
    return (
        f"Contexto de sentencias relevantes:\n\n{context}\n\n"
        f"Pregunta: {question}"
    )


async def stream_rag_response(
    question: str,
    results: list[SearchResult],
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted strings.

    Event types emitted:
    - data: {"type": "text", "content": "<token>"}
    - data: {"type": "sources", "sources": [...], "metadata": {...}}
    - data: {"type": "error", "message": "..."}
    """
    if not settings.google_api_key:
        yield _sse("error", {"type": "error", "message": "GOOGLE_API_KEY not configured."})
        return

    context = _build_context_block(results)
    user_msg = _build_user_message(question, context)

    client = genai.Client(api_key=settings.google_api_key)

    gen_start = time.monotonic()
    try:
        stream = client.models.generate_content_stream(
            model=settings.generation_model,
            contents=[user_msg],
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )

        for chunk in stream:
            if chunk.text:
                yield _sse("text", {"type": "text", "content": chunk.text})

    except Exception as exc:
        logger.exception("Gemini generation error")
        yield _sse("error", {"type": "error", "message": str(exc)})
        return

    gen_time_ms = (time.monotonic() - gen_start) * 1000

    # Final event: sources + metadata
    sources_payload = [
        {
            "doc_id": r.doc_id,
            "source_file": r.source_file,
            "section_type": r.section_type,
            "section_name": r.section_name,
            "chunk_text": r.chunk_text[:300] + ("…" if len(r.chunk_text) > 300 else ""),
            "semantic_score": round(r.semantic_score, 4),
            "lexical_score": round(r.lexical_score, 4),
            "rrf_score": round(r.rrf_score, 6),
        }
        for r in results
    ]

    yield _sse(
        "sources",
        {
            "type": "sources",
            "sources": sources_payload,
            "metadata": {
                "model": settings.generation_model,
                "generation_time_ms": round(gen_time_ms, 1),
                "sources_count": len(results),
            },
        },
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
