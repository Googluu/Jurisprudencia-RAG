"""
Text chunker that respects section boundaries.

Strategy: split by word count with overlap.
- chunk_size  ~500 words  ≈ 600-700 tokens — enough context for RAG retrieval.
- chunk_overlap ~50 words — preserves continuity at chunk edges.

A chunk never crosses a section boundary so that citations always map to a
single, unambiguous section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ingestion.parser import TextBlock


@dataclass
class Chunk:
    doc_id: str
    source_file: str
    chunk_index: int
    chunk_text: str
    section_type: str
    section_name: str
    word_count: int


def _split_words(text: str) -> list[str]:
    return re.split(r"\s+", text.strip())


def _chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Split text into overlapping word-count windows."""
    words = _split_words(text)
    if len(words) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks


def build_chunks(
    blocks: list[TextBlock],
    doc_id: str,
    source_file: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """Convert parsed TextBlocks into indexed Chunks."""
    result: list[Chunk] = []
    idx = 0

    for block in blocks:
        for piece in _chunk_text(block.text, chunk_size, overlap):
            piece = piece.strip()
            if not piece:
                continue
            result.append(
                Chunk(
                    doc_id=doc_id,
                    source_file=source_file,
                    chunk_index=idx,
                    chunk_text=piece,
                    section_type=block.section_type,
                    section_name=block.section_name,
                    word_count=len(_split_words(piece)),
                )
            )
            idx += 1

    return result
