"""Tests for HTML parser and section detector."""

import textwrap
from pathlib import Path

import pytest

from app.ingestion.parser import (
    SECTION_ANTECEDENTES,
    SECTION_CONSIDERACIONES,
    SECTION_DECISION,
    SECTION_ENCABEZADO,
    _classify_heading,
    parse_html,
)


# ---------------------------------------------------------------------------
# _classify_heading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected_type",
    [
        ("ANTECEDENTES", SECTION_ANTECEDENTES),
        ("  antecedentes  ", SECTION_ANTECEDENTES),
        ("I. ANTECEDENTES", SECTION_ANTECEDENTES),
        ("CONSIDERACIONES", SECTION_CONSIDERACIONES),
        ("SE CONSIDERA", SECTION_CONSIDERACIONES),
        ("II. CONSIDERACIONES:", SECTION_CONSIDERACIONES),
        ("DECISIÓN", SECTION_DECISION),
        ("V.-\tDECISIÓN", SECTION_DECISION),
        ("RESUELVE", SECTION_DECISION),
        ("RESUELVE:", SECTION_DECISION),
    ],
)
def test_classify_heading_matches(text, expected_type):
    result = _classify_heading(text)
    assert result is not None, f"Expected match for {text!r}"
    assert result[0] == expected_type


@pytest.mark.parametrize(
    "text",
    [
        "El demandante alegó que…",
        "CARGO PRIMERO",      # sub-section, not a top-level boundary
        "",
        "   ",
    ],
)
def test_classify_heading_no_match(text):
    result = _classify_heading(text)
    assert result is None, f"Expected no match for {text!r}"


# ---------------------------------------------------------------------------
# parse_html — integration test over a synthetic HTML file
# ---------------------------------------------------------------------------


def _make_html(body: str) -> str:
    return f"<html><body>{body}</body></html>"


def test_parse_html_four_sections(tmp_path: Path):
    html = _make_html(
        """
        <p>CORTE SUPREMA DE JUSTICIA — Magistrado: FULANO</p>
        <p>ANTECEDENTES</p>
        <p>Los hechos del caso son los siguientes...</p>
        <p>CONSIDERACIONES</p>
        <p>La Corte, en su análisis jurídico, determina que...</p>
        <p>DECISIÓN</p>
        <p>En mérito de lo expuesto, la Corte decide...</p>
        """
    )
    f = tmp_path / "test.html"
    f.write_text(html, encoding="utf-8")

    blocks = parse_html(f)
    types_found = [b.section_type for b in blocks]

    assert SECTION_ENCABEZADO in types_found
    assert SECTION_ANTECEDENTES in types_found
    assert SECTION_CONSIDERACIONES in types_found
    assert SECTION_DECISION in types_found


def test_parse_html_fallback_to_encabezado(tmp_path: Path):
    """Document with no explicit section markers → everything is encabezado."""
    html = _make_html("<p>Texto sin secciones marcadas.</p><p>Párrafo dos.</p>")
    f = tmp_path / "test.html"
    f.write_text(html, encoding="utf-8")

    blocks = parse_html(f)
    assert all(b.section_type == SECTION_ENCABEZADO for b in blocks)


def test_parse_html_decision_variation(tmp_path: Path):
    """'V.- DECISIÓN' (with Roman numeral prefix) should still map to decision."""
    html = _make_html(
        """
        <p>Encabezado del documento</p>
        <p>V.- DECISIÓN</p>
        <p>En mérito de lo expuesto se resuelve...</p>
        """
    )
    f = tmp_path / "test.html"
    f.write_text(html, encoding="utf-8")

    blocks = parse_html(f)
    section_types = {b.section_type for b in blocks}
    assert SECTION_DECISION in section_types
