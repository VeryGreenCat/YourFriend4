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
    text_emotion_model_path: str = field(
        default_factory=lambda: os.getenv("TEXT_EMOTION_MODEL_PATH", "./data/models/text_emotion")
    )
    text_emotion_model_top_k: int = field(
        default_factory=lambda: int(os.getenv("TEXT_EMOTION_MODEL_TOP_K", "5"))
    )
    # LLM traits model settings
    traits_llm_model: str = field(
        default_factory=lambda: os.getenv("TRAITS_LLM_MODEL", "gpt-4o-mini")
    )
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    # Supabase settings
    Supabase_URL: str = field(
        default_factory=lambda: os.getenv("SUPABASE_URL", "")
    )
    # Use service role key for backend operations; fall back to anon key
    Supabase_Service_Key: str = field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_KEY", ""))
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
