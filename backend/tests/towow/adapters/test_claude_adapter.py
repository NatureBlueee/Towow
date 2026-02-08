"""Tests for ClaudeAdapter."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from towow.adapters.claude_adapter import ClaudeAdapter
from towow.core.errors import AdapterError


@pytest.fixture
def adapter():
    """Create a ClaudeAdapter with test profiles."""
    profiles = {
        "agent_alice": {"agent_id": "agent_alice", "name": "Alice", "skills": ["python"]},
    }
    return ClaudeAdapter(
        api_key="test-key",
        model="claude-test",
        profiles=profiles,
    )


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_returns_stored_profile(self, adapter):
        result = await adapter.get_profile("agent_alice")
        assert result["name"] == "Alice"
        assert result["skills"] == ["python"]

    @pytest.mark.asyncio
    async def test_returns_fallback_for_unknown_agent(self, adapter):
        result = await adapter.get_profile("agent_unknown")
        assert result == {"agent_id": "agent_unknown"}


class TestChat:
    @pytest.mark.asyncio
    async def test_returns_text_response(self, adapter):
        mock_response = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Hello from Claude")],
            stop_reason="end_turn",
        )
        adapter._client.messages.create = AsyncMock(return_value=mock_response)

        result = await adapter.chat(
            agent_id="agent_alice",
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert result == "Hello from Claude"
        adapter._client.messages.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_concatenates_multiple_text_blocks(self, adapter):
        mock_response = SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="Part 1 "),
                SimpleNamespace(type="text", text="Part 2"),
            ],
            stop_reason="end_turn",
        )
        adapter._client.messages.create = AsyncMock(return_value=mock_response)

        result = await adapter.chat(
            agent_id="agent_alice",
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert result == "Part 1 Part 2"

    @pytest.mark.asyncio
    async def test_passes_system_prompt(self, adapter):
        mock_response = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="OK")],
            stop_reason="end_turn",
        )
        adapter._client.messages.create = AsyncMock(return_value=mock_response)

        await adapter.chat(
            agent_id="agent_alice",
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="You are helpful.",
        )

        call_kwargs = adapter._client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are helpful."

    @pytest.mark.asyncio
    async def test_raises_adapter_error_on_api_failure(self, adapter):
        import anthropic

        adapter._client.messages.create = AsyncMock(
            side_effect=anthropic.APIError(
                message="Rate limit",
                request=MagicMock(),
                body=None,
            )
        )

        with pytest.raises(AdapterError, match="Claude API call failed"):
            await adapter.chat(
                agent_id="agent_alice",
                messages=[{"role": "user", "content": "Hi"}],
            )


class TestChatStream:
    @pytest.mark.asyncio
    async def test_yields_text_chunks(self, adapter):
        # Build an async context manager that yields text chunks
        class FakeTextStream:
            def __aiter__(self):
                return self

            async def __anext__(self):
                if not hasattr(self, "_items"):
                    self._items = iter(["chunk1", "chunk2"])
                try:
                    return next(self._items)
                except StopIteration:
                    raise StopAsyncIteration

        class FakeStream:
            def __init__(self):
                self.text_stream = FakeTextStream()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        adapter._client.messages.stream = MagicMock(return_value=FakeStream())

        chunks = []
        async for chunk in adapter.chat_stream(
            agent_id="agent_alice",
            messages=[{"role": "user", "content": "Hi"}],
        ):
            chunks.append(chunk)

        assert chunks == ["chunk1", "chunk2"]
