import os
from dataclasses import dataclass, field


@dataclass
class ApiConfig:
    # Neo4j
    graph_db_uri: str = field(
        default_factory=lambda: os.getenv("GRAPH_DATABASE_URI", "neo4j://localhost")
    )
    graph_db_user: str = field(
        default_factory=lambda: os.getenv("GRAPH_DATABASE_USERNAME", "")
    )
    graph_db_password: str = field(
        default_factory=lambda: os.getenv("GRAPH_DATABASE_PASSWORD", "")
    )

    # JWT
    jwt_secret: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET", "change-me-in-production")
    )
    jwt_algorithm: str = field(
        default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256")
    )
    jwt_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    )

    # App
    app_env: str = field(
        default_factory=lambda: os.getenv("APP_ENV", "development")
    )


_config: ApiConfig | None = None


def get_api_config() -> ApiConfig:
    global _config
    if _config is None:
        _config = ApiConfig()
    return _config
