import os
from dataclasses import dataclass, field


@dataclass
class ApiConfig:
    # Secret used to sign/verify profile cookies issued by this API
    jwt_secret: str = field(
        default_factory=lambda: os.getenv("API_JWT_SECRET", "change-me-in-production")
    )
    jwt_algorithm: str = "HS256"
    # Supabase project JWT secret – used to verify incoming Supabase access tokens
    supabase_jwt_secret: str = field(
        default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET", "")
    )


_api_config: ApiConfig | None = None


def get_api_config() -> ApiConfig:
    global _api_config
    if _api_config is None:
        _api_config = ApiConfig()
    return _api_config
