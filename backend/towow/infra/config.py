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
    default_model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096

    # Center coordination
    max_center_rounds: int = 2

    # Offer collection
    offer_timeout_seconds: float = 30.0

    # Resonance
    default_k_star: int = 5
    embedding_dim: int = 128
