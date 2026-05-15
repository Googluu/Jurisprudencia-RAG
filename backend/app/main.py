"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.store import store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading index…")
    try:
        store.load()
    except FileNotFoundError as exc:
        logger.warning("%s — API will return 503 until pipeline is run.", exc)
    yield
    logger.info("Shutdown.")


app = FastAPI(
    title="Jurisprudencia RAG API",
    description=(
        "API de preguntas y respuestas sobre jurisprudencia de la Corte Suprema "
        "de Justicia, Sala de Casación Civil. Implementa búsqueda híbrida "
        "(semántica + BM25) y generación con Gemini vía streaming SSE."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
