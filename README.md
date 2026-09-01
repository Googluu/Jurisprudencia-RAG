# Jurisprudencia RAG — Corte Suprema de Justicia, Sala de Casación Civil

Aplicación fullstack de preguntas y respuestas sobre jurisprudencia. Procesa 100 sentencias HTML, genera embeddings con Gemini, expone una API RAG con streaming SSE y las sirve desde una interfaz Next.js con efecto typing y visualización de fuentes por sección.

---

## Estructura del proyecto

```
prueba-esguerra/
├── backend/                  # FastAPI + uv
│   ├── app/
│   │   ├── ingestion/        # pipeline: parser → chunker → embeddings
│   │   ├── search/           # semántica, BM25, fusión RRF
│   │   ├── api/              # rutas FastAPI, schemas, RAG
│   │   ├── config.py
│   │   ├── store.py          # carga índice al arrancar
│   │   └── main.py
│   ├── tests/                # 31 tests pytest
│   ├── data/                 # CSV + embeddings (generados, no en git)
│   └── pyproject.toml
├── frontend/                 # Next.js 15 + TypeScript + Tailwind
│   ├── app/
│   ├── components/
│   └── lib/
├── documentos para prueba/   # 100 HTML de sentencias
├── docker-compose.yml
└── .env.example
```

---

## Inicio rápido

### Prerrequisitos

- Python 3.12+ con [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- Clave de API de Google Gemini (`GOOGLE_API_KEY`)

### 1. Clonar repo - Variables de entorno

```bash
git clone git@github.com:Googluu/Jurisprudencia-RAG.git
cd backend
uv sync
# backend/.env
GOOGLE_API_KEY=AQ.Ab8RN6LH6ewPcpgqcfnT...
```

### 2. Pipeline de ingesta (solo la primera vez)

```bash
cd backend
uv run python -m app.ingestion.pipeline
```

Genera `backend/data/chunks.csv` y `backend/data/embeddings/index.npy`.  
En ejecuciones posteriores el servidor detecta el caché y no re-genera los embeddings.

### 3. Backend

```bash
cd backend
uv run uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 5. Con Docker (todo en un comando)

```bash
# Requiere backend/.env con GOOGLE_API_KEY
# Primero ejecutar el pipeline de ingesta una vez (ver paso 2)
docker compose up --build
```

---

## Decisiones técnicas

### Detección de secciones

Los documentos HTML provienen de un sistema judicial con markup legacy generado por OpenOffice. La estrategia es:

1. **BeautifulSoup + lxml** para parsear HTML tolerante a errores.
2. Detección de headings por etiqueta (`h1`–`h6`) y por heurística de párrafos en mayúsculas cortos (< 120 chars).
3. **Regex con prefijos romanos y variantes** (`^[\s\d\.\-IVXivx]*` antes del marcador) para cubrir casos como `"V.-\tDECISIÓN"`, `"II. CONSIDERACIONES:"`, `"RESUELVE:"`.
4. Fallback: todo el texto sin sección explícita queda como `encabezado`.

### Chunking

- **Ventana de palabras**: 500 palabras (~600-700 tokens), overlap de 50 palabras.
- **Respeta límites de sección**: un chunk nunca cruza de una sección a otra. Esto garantiza que la cita de sección en la respuesta siempre sea correcta.
- Justificación del tamaño: 500 palabras proveen contexto suficiente para razonamiento jurídico sin exceder el límite de tokens del modelo de embeddings.

### Búsqueda híbrida

Combina dos señales complementarias:

| Método | Herramienta | Fortaleza |
|--------|-------------|-----------|
| Semántica | Embeddings Gemini + similitud coseno | Captura sinónimos y paráfrasis jurídicas |
| Léxica | BM25 (rank-bm25) | Precisa para términos técnicos exactos (nombres de artículos, radicados) |

**Fusión**: Reciprocal Rank Fusion (RRF, k=60).  
RRF suma `1 / (k + rank)` por cada lista. Elegido sobre weighted sum porque:
- No requiere normalizar scores heterogéneos (coseno ∈ [-1,1] vs. BM25 ∈ [0,∞]).
- Es robusto: un documento excelente en una sola lista aún puede rankear bien.
- `k=60` es el valor estándar validado empíricamente en la literatura.

### Generación y citación

- Modelo: `gemini-2.0-flash` (mejor disponible en la familia Gemini con buen balance velocidad/calidad).
- El prompt instruye explícitamente a citar `sección tipo — nombre literal` del chunk fuente.
- `temperature=0.2` para respuestas consistentes y precisas.

### Caché de embeddings

- Matriz NumPy `.npy` + JSON de metadatos con `n_chunks` y modelo.
- Al arrancar el servidor, si `n_chunks` del caché coincide con los del CSV, se usa el caché sin llamar a Gemini.

---

## API

### `POST /api/chat/stream`

Streaming SSE. Emite tres tipos de eventos:

```
event: text
data: {"type": "text", "content": "token..."}

event: sources
data: {"type": "sources", "sources": [...], "metadata": {...}}

event: error
data: {"type": "error", "message": "..."}
```

### `POST /api/debug/retrieval`

Observabilidad completa: scores individuales semánticos y léxicos, ranking fusionado, tiempo por etapa.

### `GET /api/health`

Estado del índice cargado.

---

## Tests

```bash
cd backend
uv run pytest tests/ -v
# 31 tests — parser, chunker, búsqueda híbrida
```

Los tests de búsqueda usan embeddings aleatorios; no hacen llamadas reales a Gemini.
