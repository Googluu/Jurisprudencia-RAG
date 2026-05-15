"""
HTML parser and section detector for Corte Suprema de Justicia sentences.

Section detection uses regex over clean text with generous matching to handle
variations found in real documents: numbered headings ("V. DECISIÓN"),
accented/unaccented variants, colons, and missing sections.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Section type constants
# ---------------------------------------------------------------------------
SECTION_ENCABEZADO = "encabezado"
SECTION_ANTECEDENTES = "antecedentes"
SECTION_CONSIDERACIONES = "consideraciones"
SECTION_DECISION = "decision"

SECTION_ORDER = [
    SECTION_ENCABEZADO,
    SECTION_ANTECEDENTES,
    SECTION_CONSIDERACIONES,
    SECTION_DECISION,
]

# ---------------------------------------------------------------------------
# Patterns — ordered from most specific to most general.
# Each entry: (section_type, compiled_regex)
# ---------------------------------------------------------------------------
_DECISION_RE = re.compile(
    r"^[\s\d\.\-IVXivx]*"
    r"(DECISI[OÓ]N|RESUELVE|SE RESUELVE|PARTE RESOLUTIVA)"
    r"[\s:\.]*$",
    re.IGNORECASE | re.UNICODE,
)

_CONSIDERACIONES_RE = re.compile(
    r"^[\s\d\.\-IVXivx]*"
    r"(CONSIDERACIONES?|SE CONSIDERA|CONSIDERA(?:CION)?(?:ES)?|"
    r"FUNDAMENTOS?\s+DE\s+LA\s+DECISI[OÓ]N|AN[AÁ]LISIS)"
    r"[\s:\.]*$",
    re.IGNORECASE | re.UNICODE,
)

_ANTECEDENTES_RE = re.compile(
    r"^[\s\d\.\-IVXivx]*"
    r"(ANTECEDENTES?|HECHOS?|RELACI[OÓ]N\s+DE\s+HECHOS?|"
    r"DEMANDA|TRÁMITE|TRAMITE|PRETENSIONES?)"
    r"[\s:\.]*$",
    re.IGNORECASE | re.UNICODE,
)

_SECTION_PATTERNS = [
    (SECTION_DECISION, _DECISION_RE),
    (SECTION_CONSIDERACIONES, _CONSIDERACIONES_RE),
    (SECTION_ANTECEDENTES, _ANTECEDENTES_RE),
]


@dataclass
class TextBlock:
    """A contiguous block of text belonging to one section."""

    section_type: str
    section_name: str
    text: str


def _is_heading_candidate(tag) -> bool:
    """Return True if a tag looks like a section heading."""
    name = tag.name
    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return True
    # Paragraph-level bold/uppercase text used as headings in legacy HTML
    if name == "p":
        style = (tag.get("style") or "").lower()
        cls = " ".join(tag.get("class") or []).lower()
        if "bold" in style or "font-weight" in style or "titulo" in cls:
            return True
        text = tag.get_text(" ", strip=True)
        if text and len(text) < 120 and text == text.upper() and len(text) > 3:
            return True
    return False


def _classify_heading(text: str):
    """Return (section_type, raw_title) or None if not a section boundary."""
    clean = text.strip()
    if not clean:
        return None
    for section_type, pattern in _SECTION_PATTERNS:
        if pattern.match(clean):
            return (section_type, clean)
    return None


def _extract_paragraphs(soup: BeautifulSoup) -> list[tuple[bool, str, str]]:
    """
    Walk the document and yield (is_heading, raw_heading_text, paragraph_text).
    Tries heading detection first; falls back to paragraph extraction.
    """
    results: list[tuple[bool, str, str]] = []
    seen_text: set[str] = set()

    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div"]):
        text = tag.get_text(" ", strip=True)
        if not text or text in seen_text:
            continue
        seen_text.add(text)

        if _is_heading_candidate(tag):
            classification = _classify_heading(text)
            if classification:
                results.append((True, classification[0], classification[1]))
                continue

        if len(text) > 20:
            results.append((False, "", text))

    return results


def parse_html(file_path: Path) -> list[TextBlock]:
    """
    Parse an HTML sentence file and return a list of TextBlocks, each
    assigned to its section type and bearing the literal section title.
    """
    raw = file_path.read_bytes()
    # Try utf-8, fall back to latin-1 (common in legacy judicial HTML)
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            html = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        html = raw.decode("latin-1", errors="replace")

    soup = BeautifulSoup(html, "lxml")

    # Remove script/style noise
    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()

    paragraphs = _extract_paragraphs(soup)

    # Build blocks: accumulate text under current section
    blocks: list[TextBlock] = []
    current_type = SECTION_ENCABEZADO
    current_name = "encabezado"
    buffer: list[str] = []

    def flush():
        text = " ".join(buffer).strip()
        if text:
            blocks.append(TextBlock(current_type, current_name, text))
        buffer.clear()

    for is_heading, sec_type, text in paragraphs:
        if is_heading:
            flush()
            current_type = sec_type
            current_name = text
        else:
            buffer.append(text)

    flush()

    # If no structural sections were found, keep everything as encabezado
    return blocks
