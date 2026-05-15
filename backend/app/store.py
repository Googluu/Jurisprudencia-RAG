"""
Application-level store: loads chunks CSV + embeddings once at startup.
Also builds the BM25 index.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from app.config import settings
from app.search.lexical import build_bm25

logger = logging.getLogger(__name__)


class AppStore:
    df: pd.DataFrame
    embeddings: np.ndarray
    bm25: BM25Okapi
    ready: bool = False

    def load(self) -> None:
        if not settings.chunks_csv.exists():
            raise FileNotFoundError(
                f"chunks.csv not found at {settings.chunks_csv}. "
                "Run the ingestion pipeline first: "
                "uv run python -m app.ingestion.pipeline"
            )
        if not settings.embeddings_index.exists():
            raise FileNotFoundError(
                f"Embeddings not found at {settings.embeddings_index}. "
                "Run the ingestion pipeline first."
            )

        logger.info("Loading chunks CSV…")
        self.df = pd.read_csv(settings.chunks_csv, dtype=str)
        self.df["chunk_index"] = self.df["chunk_index"].astype(int)
        self.df["word_count"] = pd.to_numeric(self.df["word_count"], errors="coerce").fillna(0).astype(int)

        logger.info("Loading embeddings…")
        self.embeddings = np.load(str(settings.embeddings_index))

        if len(self.df) != len(self.embeddings):
            raise ValueError(
                f"CSV rows ({len(self.df)}) != embeddings rows ({len(self.embeddings)}). "
                "Re-run the pipeline."
            )

        logger.info("Building BM25 index…")
        self.bm25 = build_bm25(self.df["chunk_text"].tolist())

        self.ready = True
        logger.info(
            "Store ready: %d chunks, embeddings shape=%s",
            len(self.df),
            self.embeddings.shape,
        )


store = AppStore()
