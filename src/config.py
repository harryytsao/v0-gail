from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "GAIL_", "env_file": ".env", "extra": "ignore"}

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gail"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/gail"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    profile_cache_ttl: int = 300  # 5 minutes

    # LLM provider: "gemini", "anthropic", or "ollama"
    llm_provider: str = "gemini"

    # Gemini (used when llm_provider=gemini)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Anthropic (used when llm_provider=anthropic)
    anthropic_api_key: str = ""

    # Ollama (used when llm_provider=ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Model names (override per-provider defaults)
    extraction_model: str = ""  # auto-set from provider
    agent_model: str = ""  # auto-set from provider
    max_extraction_tokens: int = 4096
    max_agent_tokens: int = 4096

    @property
    def resolved_extraction_model(self) -> str:
        if self.extraction_model:
            return self.extraction_model
        defaults = {"gemini": self.gemini_model, "ollama": self.ollama_model, "anthropic": "claude-sonnet-4-5-20250929"}
        return defaults.get(self.llm_provider, self.gemini_model)

    @property
    def resolved_agent_model(self) -> str:
        if self.agent_model:
            return self.agent_model
        defaults = {"gemini": self.gemini_model, "ollama": self.ollama_model, "anthropic": "claude-sonnet-4-5-20250929"}
        return defaults.get(self.llm_provider, self.gemini_model)

    # Batch processing
    batch_chunk_size: int = 1000
    max_concurrent_extractions: int = 2  # Keep low for free-tier rate limits
    dataset_path: str = "conversations_merged.json"

    # Scoring
    score_decay_lambda: float = 0.03  # half-life ~23 days

    # Evolution
    consistency_threshold: float = 1.5  # std dev threshold for conflict detection
    snapshot_interval_days: int = 7

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
