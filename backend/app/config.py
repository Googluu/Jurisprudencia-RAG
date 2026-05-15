from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    google_api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_origin: str = "http://localhost:3000"

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    docs_dir: Path = Path(__file__).parent.parent.parent / "documentos para prueba"
    data_dir: Path = Path(__file__).parent.parent / "data"

    # Ingestion
    chunk_size: int = 500       # tokens aprox (chars / 4)
    chunk_overlap: int = 50

    # Models
    embedding_model: str = "gemini-embedding-001"
    generation_model: str = "gemini-2.0-flash"

    # Search
    top_k: int = 8
    semantic_weight: float = 0.6
    lexical_weight: float = 0.4
    rrf_k: int = 60

    @property
    def chunks_csv(self) -> Path:
        return self.data_dir / "chunks.csv"

    @property
    def embeddings_dir(self) -> Path:
        return self.data_dir / "embeddings"

    @property
    def embeddings_index(self) -> Path:
        return self.data_dir / "embeddings" / "index.npy"

    @property
    def embeddings_meta(self) -> Path:
        return self.data_dir / "embeddings" / "meta.json"


settings = Settings()
