"""
Ingestion pipeline: HTML → parsed sections → chunks → CSV → embeddings.

Run directly:
    uv run python -m app.ingestion.pipeline
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
from google import genai
from google.genai import types

from app.config import settings
from app.ingestion.chunker import Chunk, build_chunks
from app.ingestion.parser import parse_html

logger = logging.getLogger(__name__)

# Gemini embedding API allows max 100 texts per batch request
_BATCH_SIZE = 100


def _make_doc_id(source_file: str) -> str:
    """Derive a clean doc_id from the filename."""
    stem = Path(source_file).stem
    # Remove leading date prefix like "04-08-10- " if present
    clean = stem.replace(" ", "_").replace("(", "").replace(")", "")
    return clean


def run_parsing(docs_dir: Path, chunk_size: int, overlap: int) -> list[Chunk]:
    """Parse all HTML files and return chunks."""
    html_files = sorted(docs_dir.glob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No HTML files found in {docs_dir}")

    logger.info("Parsing %d HTML files from %s", len(html_files), docs_dir)
    all_chunks: list[Chunk] = []

    for html_file in html_files:
        try:
            blocks = parse_html(html_file)
            doc_id = _make_doc_id(html_file.name)
            chunks = build_chunks(blocks, doc_id, html_file.name, chunk_size, overlap)
            all_chunks.extend(chunks)
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", html_file.name, exc)

    logger.info("Total chunks produced: %d", len(all_chunks))
    return all_chunks


def save_csv(chunks: list[Chunk], csv_path: Path) -> pd.DataFrame:
    """Persist chunks to CSV and return the dataframe."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "doc_id": c.doc_id,
            "source_file": c.source_file,
            "chunk_index": c.chunk_index,
            "chunk_text": c.chunk_text,
            "section_type": c.section_type,
            "section_name": c.section_name,
            "word_count": c.word_count,
        }
        for c in chunks
    ]
    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info("CSV saved to %s (%d rows)", csv_path, len(df))
    return df


def _cache_is_valid(meta_path: Path, index_path: Path, n_chunks: int) -> bool:
    """Return True if the cached embeddings match the current chunk count."""
    if not meta_path.exists() or not index_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text())
        return meta.get("n_chunks") == n_chunks
    except Exception:
        return False


def generate_embeddings(
    texts: list[str],
    index_path: Path,
    meta_path: Path,
) -> np.ndarray:
    """
    Generate or load cached embeddings.

    Embeddings are stored as float32 NumPy array (n_chunks, dim).
    Meta JSON records n_chunks and model so we can detect stale caches.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(texts)

    if _cache_is_valid(meta_path, index_path, n):
        logger.info("Loading embeddings from cache (%d chunks)", n)
        return np.load(str(index_path))

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY not set — cannot generate embeddings.")

    logger.info("Generating embeddings for %d chunks via Gemini…", n)
    client = genai.Client(api_key=settings.google_api_key)
    embeddings: list[list[float]] = []

    for batch_start in range(0, n, _BATCH_SIZE):
        batch = texts[batch_start : batch_start + _BATCH_SIZE]
        logger.info(
            "  batch %d-%d / %d", batch_start + 1, batch_start + len(batch), n
        )
        for attempt in range(3):
            try:
                response = client.models.embed_content(
                    model=settings.embedding_model,
                    contents=batch,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
                )
                embeddings.extend([e.values for e in response.embeddings])
                break
            except Exception as exc:
                if attempt == 2:
                    raise
                logger.warning("Retry %d after error: %s", attempt + 1, exc)
                time.sleep(2 ** attempt)

    matrix = np.array(embeddings, dtype=np.float32)
    np.save(str(index_path), matrix)

    meta = {
        "n_chunks": n,
        "model": settings.embedding_model,
        "dim": matrix.shape[1] if matrix.ndim > 1 else 0,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    logger.info("Embeddings saved to %s shape=%s", index_path, matrix.shape)
    return matrix


def run_full_pipeline() -> tuple[pd.DataFrame, np.ndarray]:
    """
    Full pipeline: parse → CSV → embeddings.
    Returns (dataframe, embeddings_matrix).
    """
    chunks = run_parsing(
        settings.docs_dir,
        settings.chunk_size,
        settings.chunk_overlap,
    )

    df = save_csv(chunks, settings.chunks_csv)

    matrix = generate_embeddings(
        texts=df["chunk_text"].tolist(),
        index_path=settings.embeddings_index,
        meta_path=settings.embeddings_meta,
    )

    return df, matrix


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_full_pipeline()
    print("Pipeline completed successfully.")
