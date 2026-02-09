"""
ClaudeAdapter — Default adapter for users without their own LLM.

Uses the Anthropic Claude API as a client-side adapter, providing
get_profile/chat/chat_stream that match the ProfileDataSource Protocol.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Optional

import anthropic

from towow.core.errors import AdapterError

from .base import BaseAdapter

logger = logging.getLogger(__name__)


class ClaudeAdapter(BaseAdapter):
    """
    Default client-side adapter using Anthropic Claude API.

    For users who don't have their own LLM (no SecondMe, etc.),
    this adapter provides a default Claude channel for Formulation
    and Offer generation.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 4096,
        profiles: dict[str, dict[str, Any]] | None = None,
    ):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        # V1: profile data is stored in-memory, passed at construction
        self._profiles = profiles if profiles is not None else {}

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        """Return stored profile data. V1 returns from in-memory store."""
        return self._profiles.get(agent_id, {"agent_id": agent_id})

    async def chat(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send messages to Claude API, return response text."""
        try:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": messages,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await self._client.messages.create(**kwargs)

            # Extract text from response content blocks
            text_parts = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
            return "".join(text_parts)

        except anthropic.APIError as e:
            logger.error(f"Claude API error for agent {agent_id}: {e}")
            raise AdapterError(f"Claude API call failed: {e}") from e

    async def chat_stream(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream responses from Claude API, yielding text chunks."""
        try:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": messages,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        except anthropic.APIError as e:
            logger.error(f"Claude stream error for agent {agent_id}: {e}")
            raise AdapterError(f"Claude stream failed: {e}") from e
