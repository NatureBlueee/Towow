"""Tests for ClaudePlatformClient."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from towow.infra.llm_client import ClaudePlatformClient
from towow.core.errors import LLMError


@pytest.fixture
def client():
    return ClaudePlatformClient(api_key="test-key", model="claude-test")


class TestChat:
    @pytest.mark.asyncio
    async def test_text_only_response(self, client):
        mock_response = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="The answer is 42.")],
            stop_reason="end_turn",
        )
        client._clients[0].messages.create = AsyncMock(return_value=mock_response)

        result = await client.chat(
            messages=[{"role": "user", "content": "What is the answer?"}],
        )

        assert result["content"] == "The answer is 42."
        assert result["tool_calls"] is None
        assert result["stop_reason"] == "end_turn"

    @pytest.mark.asyncio
    async def test_tool_use_response(self, client):
        mock_response = SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name="output_plan",
                    input={"plan_text": "Build this."},
                    id="call_123",
                ),
            ],
            stop_reason="tool_use",
        )
        client._clients[0].messages.create = AsyncMock(return_value=mock_response)

        result = await client.chat(
            messages=[{"role": "user", "content": "Make a plan"}],
            tools=[{"name": "output_plan", "description": "...", "input_schema": {}}],
        )

        assert result["content"] is None
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "output_plan"
        assert result["tool_calls"][0]["arguments"] == {"plan_text": "Build this."}
        assert result["tool_calls"][0]["id"] == "call_123"
        assert result["stop_reason"] == "tool_use"

    @pytest.mark.asyncio
    async def test_mixed_text_and_tool_response(self, client):
        mock_response = SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="Let me help. "),
                SimpleNamespace(
                    type="tool_use",
                    name="ask_agent",
                    input={"agent_id": "a1", "question": "What do you offer?"},
                    id="call_456",
                ),
            ],
            stop_reason="tool_use",
        )
        client._clients[0].messages.create = AsyncMock(return_value=mock_response)

        result = await client.chat(
            messages=[{"role": "user", "content": "Coordinate"}],
        )

        assert result["content"] == "Let me help. "
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "ask_agent"

    @pytest.mark.asyncio
    async def test_passes_system_and_tools(self, client):
        mock_response = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="OK")],
            stop_reason="end_turn",
        )
        client._clients[0].messages.create = AsyncMock(return_value=mock_response)

        tools = [{"name": "test_tool", "description": "A tool", "input_schema": {"type": "object"}}]
        await client.chat(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Be helpful.",
            tools=tools,
        )

        call_kwargs = client._clients[0].messages.create.call_args[1]
        assert call_kwargs["system"] == "Be helpful."
        assert call_kwargs["tools"] == tools

    @pytest.mark.asyncio
    async def test_raises_llm_error_on_api_failure(self, client):
        import anthropic

        client._clients[0].messages.create = AsyncMock(
            side_effect=anthropic.APIError(
                message="Server error",
                request=MagicMock(),
                body=None,
            )
        )

        with pytest.raises(LLMError, match="Platform LLM call failed"):
            await client.chat(
                messages=[{"role": "user", "content": "Hi"}],
            )
