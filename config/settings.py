"""
Centralized configuration for the arXiv RAG system.
All values are loaded from environment variables / .env so the same
codebase runs unchanged across dev, staging, and prod (no Docker required).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # arXiv
    arxiv_category: str = "cs.AI"
    arxiv_max_results: int = 50
    arxiv_rate_limit_seconds: float = 3.0

    # Neon Postgres
    neon_database_url: str

    # OpenSearch
    opensearch_host: str
    opensearch_user: str = ""
    opensearch_password: str = ""
    opensearch_index: str = "arxiv-papers"
    opensearch_verify_certs: bool = True

    # Jina
    jina_api_key: str
    jina_model: str = "jina-embeddings-v3"
    jina_embedding_dim: int = 1024

    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl_seconds: int = 3600

    # LangFuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # Airflow
    airflow_base_url: str = "http://localhost:8080"
    airflow_username: str = "admin"
    airflow_password: str = "admin"
    airflow_dag_id: str = "arxiv_ingestion_dag"

    # App
    pdf_cache_dir: str = "./pdf_cache"
    log_level: str = "INFO"
    guardrail_score_threshold: int = 60
    max_rag_retries: int = 2


settings = Settings()
