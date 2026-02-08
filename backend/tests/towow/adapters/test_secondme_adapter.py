"""Tests for SecondMeAdapter."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from towow.adapters.secondme_adapter import SecondMeAdapter
from towow.core.errors import AdapterError


@pytest.fixture
def mock_oauth2_client():
    """Create a mock SecondMeOAuth2Client."""
    client = AsyncMock()
    return client


@pytest.fixture
def adapter(mock_oauth2_client):
    profiles = {
        "agent_bob": {"agent_id": "agent_bob", "name": "Bob"},
    }
    return SecondMeAdapter(
        oauth2_client=mock_oauth2_client,
        access_token="test-token",
        profiles=profiles,
    )


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_returns_stored_profile(self, adapter):
        result = await adapter.get_profile("agent_bob")
        assert result["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_falls_back_to_secondme_api(self, adapter, mock_oauth2_client):
        mock_oauth2_client.get_user_info.return_value = SimpleNamespace(
            name="Carol",
            bio="Developer",
            self_introduction="I build things",
        )

        result = await adapter.get_profile("agent_unknown")
        assert result["name"] == "Carol"
        assert result["bio"] == "Developer"

    @pytest.mark.asyncio
    async def test_returns_minimal_on_api_failure(self, adapter, mock_oauth2_client):
        mock_oauth2_client.get_user_info.side_effect = Exception("API down")

        result = await adapter.get_profile("agent_unknown")
        assert result == {"agent_id": "agent_unknown"}


class TestChat:
    @pytest.mark.asyncio
    async def test_collects_stream_into_full_response(self, adapter, mock_oauth2_client):
        async def fake_stream(**kwargs):
            yield {"type": "data", "content": "Hello "}
            yield {"type": "data", "content": "World"}
            yield {"type": "done"}

        mock_oauth2_client.chat_stream = fake_stream

        result = await adapter.chat(
            agent_id="agent_bob",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result == "Hello World"


class TestChatStream:
    @pytest.mark.asyncio
    async def test_yields_data_content(self, adapter, mock_oauth2_client):
        async def fake_stream(**kwargs):
            yield {"type": "session", "sessionId": "s1"}
            yield {"type": "data", "content": "chunk1"}
            yield {"type": "data", "content": "chunk2"}
            yield {"type": "done"}

        mock_oauth2_client.chat_stream = fake_stream

        chunks = []
        async for chunk in adapter.chat_stream(
            agent_id="agent_bob",
            messages=[{"role": "user", "content": "Hi"}],
        ):
            chunks.append(chunk)

        assert chunks == ["chunk1", "chunk2"]

    @pytest.mark.asyncio
    async def test_skips_empty_content(self, adapter, mock_oauth2_client):
        async def fake_stream(**kwargs):
            yield {"type": "data", "content": ""}
            yield {"type": "data", "content": "real"}
            yield {"type": "done"}

        mock_oauth2_client.chat_stream = fake_stream

        chunks = []
        async for chunk in adapter.chat_stream(
            agent_id="agent_bob",
            messages=[{"role": "user", "content": "Hi"}],
        ):
            chunks.append(chunk)

        assert chunks == ["real"]

    @pytest.mark.asyncio
    async def test_raises_adapter_error_on_failure(self, adapter, mock_oauth2_client):
        async def failing_stream(**kwargs):
            raise Exception("Connection reset")
            yield  # pragma: no cover

        mock_oauth2_client.chat_stream = failing_stream

        with pytest.raises(AdapterError, match="SecondMe chat failed"):
            async for _ in adapter.chat_stream(
                agent_id="agent_bob",
                messages=[{"role": "user", "content": "Hi"}],
            ):
                pass
