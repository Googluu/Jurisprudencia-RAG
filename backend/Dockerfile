FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev group in production)
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ ./app/
COPY main.py ./

# Data directory (embeddings + CSV mounted via volume in compose)
RUN mkdir -p data/embeddings

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
