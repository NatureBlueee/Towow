"""
Configuration management using pydantic-settings.

All Towow-specific settings are loaded from environment variables
with the TOWOW_ prefix.
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


class TowowConfig(BaseSettings):
    """
    Towow platform configuration.

    Environment variables are prefixed with TOWOW_, e.g.:
    - TOWOW_ANTHROPIC_API_KEY=sk-...
    - TOWOW_DEFAULT_MODEL=claude-sonnet-4-5-20250929
    """

    model_config = {"env_prefix": "TOWOW_"}

    # LLM
    anthropic_api_key: str = ""
    anthropic_api_keys: str = ""  # Comma-separated keys for round-robin
    anthropic_base_url: str = ""  # Proxy base URL (e.g. https://www.packyapi.com)
    default_model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096

    def get_api_keys(self) -> list[str]:
        """Return list of API keys (multi-key preferred, fallback to single)."""
        if self.anthropic_api_keys:
            return [k.strip() for k in self.anthropic_api_keys.split(",") if k.strip()]
        if self.anthropic_api_key:
            return [self.anthropic_api_key]
        return []

    def get_base_url(self) -> str | None:
        """Return base URL or None for Anthropic default."""
        return self.anthropic_base_url or None

    # Center coordination
    max_center_rounds: int = 2

    # Offer collection
    offer_timeout_seconds: float = 30.0

    # Resonance
    default_k_star: int = 5
    embedding_dim: int = 128
