from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        examples=["¿Qué criterios usa la Corte para determinar la culpa en contratos de mandato?"],
    )
    top_k: int = Field(default=8, ge=1, le=20)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "¿Qué criterios usa la Corte para determinar la culpa en contratos de mandato?",
                    "top_k": 8,
                }
            ]
        }
    }


class SourceDocument(BaseModel):
    doc_id: str
    source_file: str
    section_type: str
    section_name: str
    chunk_text: str
    semantic_score: float
    lexical_score: float
    rrf_score: float

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "doc_id": "01-09-10-0500131030012003-00400-01",
                    "source_file": "01-09-10- (0500131030012003-00400-01).html",
                    "section_type": "consideraciones",
                    "section_name": "CONSIDERACIONES",
                    "chunk_text": "La Corte, al examinar el cargo…",
                    "semantic_score": 0.87,
                    "lexical_score": 4.21,
                    "rrf_score": 0.016,
                }
            ]
        }
    }


class QueryMetadata(BaseModel):
    model: str
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    sources_count: int


# SSE event shapes (used internally, not as response models)
class SSETextEvent(BaseModel):
    type: str = "text"
    content: str


class SSESourcesEvent(BaseModel):
    type: str = "sources"
    sources: list[SourceDocument]
    metadata: QueryMetadata


class SSEErrorEvent(BaseModel):
    type: str = "error"
    message: str


# Observability endpoint response
class ObservabilityResult(BaseModel):
    question: str
    retrieval_time_ms: float
    semantic_hits: list[dict]
    lexical_hits: list[dict]
    fused_results: list[SourceDocument]
