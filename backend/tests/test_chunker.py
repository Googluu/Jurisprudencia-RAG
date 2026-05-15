"""Tests for the text chunker."""

import pytest

from app.ingestion.chunker import _chunk_text, _split_words, build_chunks
from app.ingestion.parser import TextBlock


def test_split_words_basic():
    assert _split_words("hola mundo test") == ["hola", "mundo", "test"]


def test_chunk_text_short_no_split():
    text = " ".join(["palabra"] * 100)
    chunks = _chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_splits_correctly():
    text = " ".join([f"w{i}" for i in range(600)])
    chunks = _chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 2
    # Each chunk should not exceed chunk_size words
    for chunk in chunks:
        assert len(_split_words(chunk)) <= 500


def test_chunk_text_overlap():
    words = [f"w{i}" for i in range(600)]
    text = " ".join(words)
    chunks = _chunk_text(text, chunk_size=500, overlap=50)
    # The last 50 words of chunk 0 should appear at the start of chunk 1
    tail_words = _split_words(chunks[0])[-50:]
    head_words = _split_words(chunks[1])[:50]
    assert tail_words == head_words


def test_chunk_never_crosses_section():
    blocks = [
        TextBlock(section_type="antecedentes", section_name="ANTECEDENTES", text="A " * 300),
        TextBlock(section_type="consideraciones", section_name="CONSIDERACIONES", text="C " * 300),
    ]
    chunks = build_chunks(blocks, doc_id="doc1", source_file="f.html", chunk_size=500, overlap=50)

    # Verify section integrity: each chunk belongs to one section type
    antecedentes_chunks = [c for c in chunks if c.section_type == "antecedentes"]
    consideraciones_chunks = [c for c in chunks if c.section_type == "consideraciones"]
    assert antecedentes_chunks, "Expected antecedentes chunks"
    assert consideraciones_chunks, "Expected consideraciones chunks"

    for c in antecedentes_chunks:
        assert "C" not in c.chunk_text.replace("antecedentes", "")  # no bleed from other section


def test_build_chunks_indices_sequential():
    blocks = [
        TextBlock("encabezado", "encabezado", "texto " * 10),
        TextBlock("decision", "DECISIÓN", "resuelve " * 10),
    ]
    chunks = build_chunks(blocks, doc_id="d", source_file="x.html")
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))
