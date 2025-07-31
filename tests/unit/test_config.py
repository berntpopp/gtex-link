"""Tests for configuration validation."""

import pytest
from pydantic import ValidationError

from gtex_link.config import (
    GTExAPIConfigModel,
    ServerSettings,
)


class TestGTExAPIConfigModel:
    """Tests for GTExAPIConfigModel validators."""

    def test_validate_base_url_adds_trailing_slash(self):
        """Test that base_url validator adds trailing slash when missing."""
        config = GTExAPIConfigModel(base_url="https://gtexportal.org/api/v2")
        assert config.base_url == "https://gtexportal.org/api/v2/"

    def test_validate_base_url_keeps_trailing_slash(self):
        """Test that base_url validator keeps existing trailing slash."""
        config = GTExAPIConfigModel(base_url="https://gtexportal.org/api/v2/")
        assert config.base_url == "https://gtexportal.org/api/v2/"


class TestServerSettings:
    """Tests for ServerSettings validators."""

    def test_validate_mcp_path_adds_leading_slash(self):
        """Test that mcp_path validator adds leading slash when missing."""
        settings = ServerSettings(mcp_path="gtex-link")
        assert settings.mcp_path == "/gtex-link"

    def test_validate_mcp_path_keeps_leading_slash(self):
        """Test that mcp_path validator keeps existing leading slash."""
        settings = ServerSettings(mcp_path="/gtex-link")
        assert settings.mcp_path == "/gtex-link"

    def test_parse_cors_origins_from_string(self):
        """Test parsing CORS origins from comma-separated string."""
        settings = ServerSettings(
            cors_origins="http://localhost:3000, https://example.com,  https://test.com  "
        )
        expected = ["http://localhost:3000", "https://example.com", "https://test.com"]
        assert settings.cors_origins == expected

    def test_parse_cors_origins_from_list(self):
        """Test that CORS origins list is preserved when already a list."""
        origins = ["http://localhost:3000", "https://example.com"]
        settings = ServerSettings(cors_origins=origins)
        assert settings.cors_origins == origins

    def test_parse_cors_origins_empty_string(self):
        """Test parsing CORS origins from empty string."""
        settings = ServerSettings(cors_origins="")
        assert settings.cors_origins == []

    def test_parse_cors_origins_with_empty_items(self):
        """Test parsing CORS origins with empty items in string."""
        settings = ServerSettings(cors_origins="http://localhost:3000,  ,https://example.com, ")
        expected = ["http://localhost:3000", "https://example.com"]
        assert settings.cors_origins == expected


class TestConfigDefaults:
    """Tests for configuration defaults and validation."""

    def test_gtex_api_config_defaults(self):
        """Test GTExAPIConfigModel default values."""
        config = GTExAPIConfigModel()
        assert config.base_url == "https://gtexportal.org/api/v2/"
        assert config.timeout == 30.0
        assert config.rate_limit_per_second == 5.0
        assert config.burst_size == 10

    def test_server_settings_defaults(self):
        """Test ServerSettings default values."""
        settings = ServerSettings()
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000
        assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]
        assert settings.mcp_path == "/mcp"


class TestConfigAccessors:
    """Tests for configuration accessor functions."""

    def test_get_api_config(self):
        """Test get_api_config function returns correct config."""
        from gtex_link.config import get_api_config

        api_config = get_api_config()
        assert isinstance(api_config, GTExAPIConfigModel)
        assert api_config.base_url == "https://gtexportal.org/api/v2/"

    def test_get_cache_config(self):
        """Test get_cache_config function returns correct config."""
        from gtex_link.config import get_cache_config, CacheConfigModel

        cache_config = get_cache_config()
        assert isinstance(cache_config, CacheConfigModel)
        assert cache_config.size == 1000
        assert cache_config.ttl == 3600
