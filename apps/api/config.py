"""API configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEV_SECRET = "dev-only-not-for-production-use-32b-minimum-key"


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./openworld.db"
    secret_key: str = DEFAULT_DEV_SECRET
    demo_mode: bool = True
    log_level: str = "INFO"
    environment: str = "local"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "openworld"
    jwt_audience: str = "openworld-agents"
    jwt_expire_minutes: int = 60

    # Policy: when True, unmatched policies deny (production). Demo mode overrides to allow.
    policy_default_deny: bool = True

    # Gateway bounds (bytes). Rate limiting stays a pluggable NoOp by default.
    max_request_bytes: int = 1_048_576
    max_response_bytes: int = 10_485_760
    db_pool_size: int = 5
    db_max_overflow: int = 10

    model_config = SettingsConfigDict(env_prefix="OPENWORLD_", env_file=".env")

    @property
    def effective_default_deny(self) -> bool:
        """Demo mode uses default-allow for simulation; production uses default-deny."""
        if self.demo_mode:
            return False
        return self.policy_default_deny

    @property
    def is_production(self) -> bool:
        return not self.demo_mode

    def validate_production_safety(self) -> None:
        """Fail fast when production/staging mode is misconfigured."""
        env_name = self.environment.strip().lower()
        enforce = (not self.demo_mode) or env_name in {"production", "staging"}
        if not enforce:
            return
        errors: list[str] = []
        if env_name in {"production", "staging"} and self.demo_mode:
            errors.append("staging/production cannot run with OPENWORLD_DEMO_MODE=true")
        if self.database_url.startswith("sqlite"):
            errors.append("Production requires PostgreSQL OPENWORLD_DATABASE_URL")
        if self.secret_key == DEFAULT_DEV_SECRET:
            errors.append("Production requires a non-default OPENWORLD_SECRET_KEY")
        if len(self.secret_key) < 32:
            errors.append("OPENWORLD_SECRET_KEY must be at least 32 characters")
        if errors:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))


settings = Settings()
