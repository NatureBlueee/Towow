"""Tests for TowowConfig."""

from __future__ import annotations

import os

import pytest

from towow.infra.config import TowowConfig


class TestTowowConfig:
    def test_default_values(self):
        config = TowowConfig()
        assert config.anthropic_api_key == ""
        assert config.default_model == "claude-sonnet-4-5-20250929"
        assert config.max_tokens == 4096
        assert config.max_center_rounds == 2
        assert config.offer_timeout_seconds == 30.0
        assert config.default_k_star == 5
        assert config.embedding_dim == 128

    def test_loads_from_env(self, monkeypatch):
        monkeypatch.setenv("TOWOW_ANTHROPIC_API_KEY", "sk-test-key")
        monkeypatch.setenv("TOWOW_DEFAULT_MODEL", "claude-opus-4-6")
        monkeypatch.setenv("TOWOW_MAX_CENTER_ROUNDS", "5")
        monkeypatch.setenv("TOWOW_OFFER_TIMEOUT_SECONDS", "60.0")

        config = TowowConfig()
        assert config.anthropic_api_key == "sk-test-key"
        assert config.default_model == "claude-opus-4-6"
        assert config.max_center_rounds == 5
        assert config.offer_timeout_seconds == 60.0
