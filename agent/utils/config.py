import os
from dataclasses import dataclass, field


@dataclass
class Config:
    GraphDatabase_URI: str = field(
        default_factory=lambda: os.getenv("GRAPH_DATABASE_URI", "neo4j://localhost")
    )
    GraphDatabase_Username: str = field(
        default_factory=lambda: os.getenv("GRAPH_DATABASE_USERNAME", "")
    )
    GraphDatabase_Password: str = field(
        default_factory=lambda: os.getenv("GRAPH_DATABASE_PASSWORD", "")
    )
    # LLM traits model settings
    traits_llm_model: str = field(
        default_factory=lambda: os.getenv("TRAITS_LLM_MODEL", "deepseek-v3.2:cloud")
    )
    llm_backend: str = field(default_factory=lambda: os.getenv("LLM_BACKEND", "ollama"))
    ollama_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434")
    )
    ollama_api_key: str = field(default_factory=lambda: os.getenv("OLLAMA_API_KEY", ""))
    ollama_timeout: int = field(
        default_factory=lambda: int(os.getenv("OLLAMA_TIMEOUT", "300"))
    )
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    spliting_model: str = field(
        default_factory=lambda: os.getenv(
            "SPLITING_MODEL", "sentence-transformers/all-mpnet-base-v2"
        )
    )
    spliting_model_path: str = field(
        default_factory=lambda: os.getenv(
            "SPLITING_MODEL_PATH", "models/spliting_chunk_model"
        )
    )
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        )
    )
    embedding_model_path: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL_PATH", "models/embedding_model"
        )
    )
    # Supabase settings
    Supabase_URL: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    # Use service role key for backend operations; fall back to anon key
    Supabase_Service_Key: str = field(
        default_factory=lambda: os.getenv(
            "SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_KEY", "")
        )
    )
    # Discord bot settings
    Discord_Bot_Token: str = field(
        default_factory=lambda: os.getenv("DISCORD_BOT_TOKEN", "")
    )


# Singleton
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
