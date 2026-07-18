from functools import lru_cache

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    quantgpt_env: str = Field(default="development", alias="QUANTGPT_ENV")
    quantgpt_log_level: str = Field(default="INFO", alias="QUANTGPT_LOG_LEVEL")
    quantgpt_api_url: str = Field(default="http://localhost:8000", alias="QUANTGPT_API_URL")

    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    backend_cors_origins: str = Field(default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS")
    backend_trusted_hosts: str = Field(default="localhost,127.0.0.1", alias="BACKEND_TRUSTED_HOSTS")
    rate_limit_requests: int = Field(default=120, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_auth_requests: int = Field(default=10, alias="RATE_LIMIT_AUTH_REQUESTS")
    audit_log_enabled: bool = Field(default=True, alias="AUDIT_LOG_ENABLED")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_service_name: str = Field(default="quantgpt-backend", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str = Field(default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT")

    quantgpt_jwt_secret: str = Field(alias="QUANTGPT_JWT_SECRET")
    quantgpt_jwt_algorithm: str = Field(default="HS256", alias="QUANTGPT_JWT_ALGORITHM")
    quantgpt_jwt_access_ttl_minutes: int = Field(default=30, alias="QUANTGPT_JWT_ACCESS_TTL_MINUTES")
    quantgpt_jwt_refresh_ttl_days: int = Field(default=7, alias="QUANTGPT_JWT_REFRESH_TTL_DAYS")

    quantgpt_admin_email: str = Field(alias="QUANTGPT_ADMIN_EMAIL")
    quantgpt_admin_password: str = Field(alias="QUANTGPT_ADMIN_PASSWORD")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    openalgo_base_url: str = Field(default="http://openalgo:5000", alias="OPENALGO_BASE_URL")
    openalgo_api_key: str = Field(default="", alias="OPENALGO_API_KEY")
    openalgo_websocket_url: str = Field(default="ws://openalgo:8765", alias="OPENALGO_WEBSOCKET_URL")
    openalgo_request_timeout_seconds: float = Field(default=10.0, alias="OPENALGO_REQUEST_TIMEOUT_SECONDS")
    openalgo_max_retries: int = Field(default=3, alias="OPENALGO_MAX_RETRIES")
    openalgo_cache_ttl_seconds: int = Field(default=30, alias="OPENALGO_CACHE_TTL_SECONDS")

    # Agent framework
    agent_scheduler_interval_seconds: float = Field(default=5.0, alias="AGENT_SCHEDULER_INTERVAL_SECONDS")
    agent_task_max_attempts: int = Field(default=3, alias="AGENT_TASK_MAX_ATTEMPTS")
    agent_health_check_interval_seconds: float = Field(default=60.0, alias="AGENT_HEALTH_CHECK_INTERVAL_SECONDS")
    agent_history_retention_days: int = Field(default=30, alias="AGENT_HISTORY_RETENTION_DAYS")
    agent_message_batch_size: int = Field(default=50, alias="AGENT_MESSAGE_BATCH_SIZE")

    # Strategy Research Engine
    strategy_backtest_default_lookback_days: int = Field(default=365, alias="STRATEGY_BACKTEST_DEFAULT_LOOKBACK_DAYS")
    strategy_max_concurrent_research: int = Field(default=4, alias="STRATEGY_MAX_CONCURRENT_RESEARCH")
    strategy_scheduler_interval_seconds: float = Field(default=60.0, alias="STRATEGY_SCHEDULER_INTERVAL_SECONDS")
    strategy_plugins_dir: str = Field(default="plugins/strategies", alias="STRATEGY_PLUGINS_DIR")
    strategy_marketplace_enabled: bool = Field(default=True, alias="STRATEGY_MARKETPLACE_ENABLED")

    # ML research
    ml_model_artifact_dir: str = Field(default="model_artifacts", alias="ML_MODEL_ARTIFACT_DIR")

    @field_validator("quantgpt_jwt_secret")
    @classmethod
    def _secret_must_be_set(cls, v: str) -> str:
        if not v or "change-me" in v:
            raise ValueError("QUANTGPT_JWT_SECRET must be set to a strong value")
        return v

    @field_validator("quantgpt_env")
    @classmethod
    def _env(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        v = v.lower().strip()
        if v not in allowed:
            raise ValueError(f"QUANTGPT_ENV must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def _production_security(self) -> "Settings":
        if self.is_production:
            if len(self.quantgpt_jwt_secret) < 32:
                raise ValueError("QUANTGPT_JWT_SECRET must be at least 32 characters in production")
            if self.quantgpt_admin_password.lower().startswith("changeme"):
                raise ValueError("QUANTGPT_ADMIN_PASSWORD must be changed in production")
            if any(origin.startswith("http://") for origin in self.cors_origins_list):
                raise ValueError("BACKEND_CORS_ORIGINS must use HTTPS in production")
        return self

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.quantgpt_env == "production"

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @computed_field
    @property
    def trusted_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.backend_trusted_hosts.split(",") if host.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
