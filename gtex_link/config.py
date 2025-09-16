"""Configuration management for GTEx-Link server."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GTExAPIConfigModel(BaseModel):
    """GTEx Portal API configuration model."""

    base_url: str = Field(
        default="https://gtexportal.org/api/v2/",
        description="Base URL for GTEx Portal API",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )
    rate_limit_per_second: float = Field(
        default=5.0,
        gt=0.0,
        le=20.0,
        description="API rate limit (requests per second)",
    )
    burst_size: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum burst size for rate limiting",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Delay between retry attempts in seconds",
    )
    user_agent: str = Field(
        default="GTEx-Link/0.1.0",
        description="User agent string for API requests",
    )
    endpoints: dict[str, str] = Field(
        default={
            # Reference endpoints
            "gene_search": "reference/geneSearch",
            "gene": "reference/gene",
            "transcript": "reference/transcript",
            "exon": "reference/exon",
            "neighbor_gene": "reference/neighborGene",
            # Expression endpoints
            "median_gene_expression": "expression/medianGeneExpression",
            "median_transcript_expression": "expression/medianTranscriptExpression",
            "median_exon_expression": "expression/medianExonExpression",
            "median_junction_expression": "expression/medianJunctionExpression",
            "top_expressed_gene": "expression/topExpressedGene",
            "gene_expression": "expression/geneExpression",
            "single_nucleus_gene_expression": "expression/singleNucleusGeneExpression",
            # Dataset endpoints
            "tissue_site_detail": "dataset/tissueSiteDetail",
            "sample": "dataset/sample",
            "subject": "dataset/subject",
            "variant": "dataset/variant",
            "variant_by_location": "dataset/variantByLocation",
            # Service info
            "service_info": "",
        },
        description="API endpoint URL patterns",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base URL ends with forward slash."""
        if not v.endswith("/"):
            return f"{v}/"
        return v


class CacheConfigModel(BaseModel):
    """Cache configuration model."""

    size: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Maximum number of cached items",
    )
    ttl: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Time-to-live for cached items in seconds",
    )
    stats_enabled: bool = Field(
        default=True,
        description="Enable cache statistics tracking",
    )
    cleanup_interval: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Cache cleanup interval in seconds",
    )


class ServerSettings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="GTEX_LINK_",
    )

    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, ge=1024, le=65535, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")

    # Transport modes
    transport_mode: Literal["stdio", "http", "unified"] = Field(
        default="unified",
        description="Server transport mode",
    )

    # MCP settings
    mcp_path: str = Field(default="/mcp", description="MCP endpoint path")

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow CORS credentials",
    )
    cors_allow_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods",
    )
    cors_allow_headers: list[str] = Field(
        default=["*"],
        description="Allowed CORS headers",
    )

    # Logging settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["json", "console"] = Field(
        default="console",
        description="Log format",
    )
    log_show_caller: bool = Field(default=False, description="Show caller info in logs")

    # API configuration
    api: GTExAPIConfigModel = Field(
        default_factory=GTExAPIConfigModel,
        description="GTEx Portal API configuration",
    )

    # Cache configuration
    cache: CacheConfigModel = Field(
        default_factory=CacheConfigModel,
        description="Caching configuration",
    )

    @field_validator("mcp_path")
    @classmethod
    def validate_mcp_path(cls, v: str) -> str:
        """Ensure MCP path starts with forward slash."""
        if not v.startswith("/"):
            return f"/{v}"
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return list(v) if v else []


# Global settings instance
settings = ServerSettings()


# Configuration accessors for backward compatibility
def get_api_config() -> GTExAPIConfigModel:
    """Get API configuration from global settings."""
    return settings.api


def get_cache_config() -> CacheConfigModel:
    """Get cache configuration from global settings."""
    return settings.cache


# Aliases for backward compatibility
APIConfig = GTExAPIConfigModel
CacheConfig = CacheConfigModel
DEFAULT_API_CONFIG = settings.api
DEFAULT_CACHE_CONFIG = settings.cache
