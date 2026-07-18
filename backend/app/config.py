"""Environment-backed application configuration for Phase 2 services."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Lazy settings that do not require external credentials during import."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ubnd_reports"

    fpt_api_key: str | None = None
    fpt_base_url: str | None = None
    fpt_embedding_api_key: str | None = None
    fpt_embedding_base_url: str | None = None

    embedding_provider: Literal["fpt"] = "fpt"
    embedding_model: str = "Vietnamese_Embedding"
    embedding_batch_size: int = Field(default=32, ge=1, le=2048)
    embedding_normalize: bool = True
    embedding_timeout_seconds: float = Field(default=120, gt=0)
    embedding_max_retries: int = Field(default=3, ge=0, le=10)
    embedding_dimension: int | None = Field(default=None, ge=1)

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "ubnd_knowledge_base"
    qdrant_distance: Literal["COSINE", "DOT", "EUCLID", "MANHATTAN"] = "COSINE"
    qdrant_upsert_batch_size: int = Field(default=64, ge=1, le=4096)
    qdrant_recreate_collection: bool = False

    knowledge_base_storage_dir: Path = Path("storage/knowledge_base")
    knowledge_base_original_dir: Path = Path("storage/knowledge_base/originals")
    knowledge_base_processed_dir: Path = Path("storage/knowledge_base/processed")
    knowledge_base_failed_dir: Path = Path("storage/knowledge_base/failed")
    max_document_size_mb: int = Field(default=50, ge=1)
    knowledge_base_seed_dir: Path | None = None
    knowledge_base_seed_mapping: Path | None = None
    operational_storage_dir: Path = Path("storage/operational_reports")
    report_output_dir: Path = Path("storage/generated_reports")
    dataset_root: Path = Path("../ubnd_report_dataset")
    allowed_cors_origins: str = "http://localhost:5173"
    duplicate_document_policy: Literal["skip", "error"] = "skip"
    run_external_integration_tests: bool = False
    run_local_integration_tests: bool = False
    postgres_test_database_url: str | None = None
    qdrant_test_url: str = "http://localhost:6333"

    rag_candidate_top_k: int = Field(default=20, ge=1, le=1000)
    rag_final_top_k: int = Field(default=5, ge=1, le=100)
    rag_max_context_tokens: int = Field(default=6000, ge=100)
    rag_default_document_status: str = "active"
    rag_enable_dense_search: bool = True
    rag_enable_lexical_search: bool = True
    rag_enable_hybrid_search: bool = True
    rag_enable_reranker: bool = True
    rag_enable_parent_expansion: bool = True
    rag_dense_weight: float = Field(default=1.0, ge=0)
    rag_lexical_weight: float = Field(default=1.0, ge=0)
    rag_rrf_k: int = Field(default=60, ge=1)
    bm25_k1: float = Field(default=1.5, gt=0)
    bm25_b: float = Field(default=0.75, ge=0, le=1)

    reranker_provider: str = "fpt"
    fpt_reranker_api_key: str | None = None
    fpt_reranker_base_url: str | None = None
    reranker_model: str = "bge-reranker-v2-m3"
    reranker_batch_size: int = Field(default=16, ge=1)
    reranker_timeout_seconds: float = Field(default=120, gt=0)
    reranker_max_retries: int = Field(default=3, ge=0, le=10)

    llm_provider: str = "fpt"
    fpt_llm_api_key: str | None = None
    fpt_llm_base_url: str | None = None
    llm_model: str = "Llama-3.3-70B-Instruct"
    llm_temperature: float = Field(default=0.1, ge=0, le=2)
    llm_max_tokens: int = Field(default=4096, ge=1)
    llm_timeout_seconds: float = Field(default=120, gt=0)
    llm_max_retries: int = Field(default=3, ge=0, le=10)
    llm_enabled: bool = False

    agent_max_steps: int = Field(default=6, ge=1, le=50)
    agent_enable_production_orchestration: bool = False

    @property
    def cors_origins(self) -> list[str]:
        """Return explicitly configured browser origins."""
        return [item.strip() for item in self.allowed_cors_origins.split(",") if item.strip()]

    @property
    def effective_embedding_api_key(self) -> str | None:
        return self.fpt_embedding_api_key or self.fpt_api_key

    @property
    def effective_embedding_base_url(self) -> str | None:
        return self.fpt_embedding_base_url or self.fpt_base_url

    @property
    def effective_reranker_api_key(self) -> str | None:
        return self.fpt_reranker_api_key or self.fpt_api_key

    @property
    def effective_reranker_base_url(self) -> str | None:
        return self.fpt_reranker_base_url or self.fpt_base_url

    @property
    def effective_llm_api_key(self) -> str | None:
        return self.fpt_llm_api_key or self.fpt_api_key

    @property
    def effective_llm_base_url(self) -> str | None:
        return self.fpt_llm_base_url or self.fpt_base_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
