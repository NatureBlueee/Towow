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
    """Adapter with pre-built profile (single-user model)."""
    return SecondMeAdapter(
        oauth2_client=mock_oauth2_client,
        access_token="test-token",
        agent_id="agent_bob",
        profile={"agent_id": "agent_bob", "name": "Bob"},
    )


@pytest.fixture
def empty_adapter(mock_oauth2_client):
    """Adapter without profile — will need to fetch on demand."""
    return SecondMeAdapter(
        oauth2_client=mock_oauth2_client,
        access_token="test-token",
    )


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_returns_stored_profile(self, adapter):
        result = await adapter.get_profile("agent_bob")
        assert result["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_auto_fetches_when_no_profile(self, empty_adapter, mock_oauth2_client):
        mock_oauth2_client.get_user_info.return_value = SimpleNamespace(
            open_id="carol_id",
            name="Carol",
            bio="Developer",
            self_introduction="I build things",
            avatar="",
            profile_completeness=50,
        )
        mock_oauth2_client.get_shades.side_effect = Exception("not available")
        mock_oauth2_client.get_softmemory.side_effect = Exception("not available")

        result = await empty_adapter.get_profile("carol_id")
        assert result["name"] == "Carol"
        assert result["agent_id"] == "carol_id"

    @pytest.mark.asyncio
    async def test_raises_on_fetch_failure(self, empty_adapter, mock_oauth2_client):
        mock_oauth2_client.get_user_info.side_effect = Exception("API down")

        with pytest.raises(AdapterError, match="Cannot build profile"):
            await empty_adapter.get_profile("agent_unknown")


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
