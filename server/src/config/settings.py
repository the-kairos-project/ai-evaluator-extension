"""
Application settings and configuration.

Loads configuration from environment variables with sensible defaults.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from src.core.exceptions import ConfigurationError


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_file": ".env"}

    # API Configuration
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")

    # Security
    secret_key: str = Field(
        default="your-secret-key-here-change-in-production",
        env="SECRET_KEY"
    )
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")

    # LLM Configuration
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")
    llm_model: Optional[str] = Field(default=None, env="LLM_MODEL")
    llm_temperature: float = Field(default=0.0, env="LLM_TEMPERATURE")
    llm_max_tokens: Optional[int] = Field(default=None, env="LLM_MAX_TOKENS")
    llm_timeout: int = Field(default=48, env="LLM_TIMEOUT")

    # OpenAI Configuration (for backward compatibility and when using OpenAI)
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-mini", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.0, env="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=4096, env="OPENAI_MAX_TOKENS")
    openai_timeout: int = Field(default=60, env="OPENAI_TIMEOUT")
    openai_organization: Optional[str] = Field(default=None, env="OPENAI_ORGANIZATION")

    # Anthropic Configuration
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-opus-20240229", env="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(default=4096, env="ANTHROPIC_MAX_TOKENS")

    # PDF Parsing Model Configuration (faster/cheaper models for PDF extraction)
    pdf_parsing_model_anthropic: str = Field(
        default="claude-3-5-haiku-20241022",
        env="PDF_PARSING_MODEL_ANTHROPIC",
        description="Fast Anthropic model for PDF parsing"
    )
    pdf_parsing_model_openai: str = Field(
        default="gpt-4o-mini",
        env="PDF_PARSING_MODEL_OPENAI",
        description="Fast OpenAI model for PDF parsing"
    )

    # Agentic framework settings
    agentic_max_retries: int = Field(default=3, env="AGENTIC_MAX_RETRIES")
    agentic_reflection_enabled: bool = Field(default=True, env="AGENTIC_REFLECTION_ENABLED")

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_ssl: bool = Field(default=False, env="REDIS_SSL")
    redis_pool_size: int = Field(default=10, env="REDIS_POOL_SIZE")

    # Logging
    log_level: str = Field(default="DEBUG", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_dir: str = Field(default="logs", env="LOG_DIR")
    
    # Verbose logging controls
    log_plugin_details: bool = Field(
        default=False, 
        env="LOG_PLUGIN_DETAILS",
        description="Log detailed plugin loading/initialization messages"
    )
    log_http_details: bool = Field(
        default=False, 
        env="LOG_HTTP_DETAILS",
        description="Log detailed HTTP request/response information"
    )
    log_health_checks: bool = Field(
        default=False, 
        env="LOG_HEALTH_CHECKS",
        description="Log health check endpoint calls"
    )

    # Monitoring
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    grafana_admin_password: str = Field(default="admin", env="GRAFANA_ADMIN_PASSWORD")

    # Session Management
    session_ttl_seconds: int = Field(default=3600, env="SESSION_TTL_SECONDS")
    session_cleanup_interval: int = Field(default=300, env="SESSION_CLEANUP_INTERVAL")
    max_sessions_per_user: int = Field(default=5, env="MAX_SESSIONS_PER_USER")

    # Plugin Configuration
    plugin_directory: str = Field(default="src/plugins", env="PLUGIN_DIRECTORY")
    plugin_auto_reload: bool = Field(default=False, env="PLUGIN_AUTO_RELOAD")
    plugin_discovery_interval: int = Field(default=60, env="PLUGIN_DISCOVERY_INTERVAL")
    plugin_timeout: int = Field(default=30, env="PLUGIN_TIMEOUT")
    plugin_max_retries: int = Field(default=3, env="PLUGIN_MAX_RETRIES")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, env="RATE_LIMIT_PERIOD")

    # LinkedIn Integration
    linkedin_cookie: Optional[str] = Field(default=None, env="LINKEDIN_COOKIE")
    linkedin_external_server_url: Optional[str] = Field(
        default=None,
        env="LINKEDIN_EXTERNAL_SERVER_URL",
        description="URL of external LinkedIn MCP server (for Docker deployments)"
    )

    # Docker/deployment specific
    docker_env: bool = Field(default=False, env="DOCKER_ENV")

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    testing: bool = Field(default=False, env="TESTING")

    @property
    def debug_mode(self) -> bool:
        """Check if running in debug mode."""
        return self.debug

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    cors_methods: List[str] = Field(default=["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], env="CORS_HEADERS")

    # Database (future use)
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")

    # Feature Flags
    enable_semantic_routing: bool = Field(default=True, env="ENABLE_SEMANTIC_ROUTING")
    enable_agentic_framework: bool = Field(default=True, env="ENABLE_AGENTIC_FRAMEWORK")
    enable_hot_reload: bool = Field(default=False, env="ENABLE_HOT_RELOAD")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    def get_llm_api_key(self, provider: Optional[str] = None) -> str:
        """Get API key for the specified or default LLM provider.

        Args:
            provider: Provider name (uses default if not specified)

        Returns:
            API key for the provider

        Raises:
            ConfigurationError: If provider is unknown or API key is not configured
        """
        provider = provider or self.llm_provider
        provider = provider.lower()

        if provider == "openai":
            if not self.openai_api_key:
                raise ConfigurationError(
                    "openai_api_key",
                    "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
                )
            return self.openai_api_key
        if provider == "anthropic":
            if not self.anthropic_api_key:
                raise ConfigurationError(
                    "anthropic_api_key",
                    "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable."
                )
            return self.anthropic_api_key

        raise ConfigurationError(
            "llm_provider",
            f"Unknown LLM provider: {provider}"
        )

    def get_llm_model(self, provider: Optional[str] = None) -> str:
        """Get model for the specified or default LLM provider.

        Args:
            provider: Provider name (uses default if not specified)

        Returns:
            Model name for the provider
        """
        provider = provider or self.llm_provider
        provider = provider.lower()

        # Check if a generic model is specified
        if self.llm_model:
            return self.llm_model

        # Fall back to provider-specific defaults
        if provider == "openai":
            return self.openai_model
        if provider == "anthropic":
            return self.anthropic_model

        raise ConfigurationError(
            "llm_provider",
            f"Unknown LLM provider: {provider}"
        )


# Global settings instance
settings = Settings()
