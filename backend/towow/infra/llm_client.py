"""
ClaudePlatformClient — Platform-side LLM client with tool-use support.

Used for Center, SubNegotiation, and GapRecursion. These are our own
Claude API calls (platform-side), not the user's model.

Multi-key round-robin: supports multiple API keys for higher throughput.
Each request picks the next key in rotation, spreading load across keys.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import os
from typing import Any, Optional

import anthropic

from towow.core.errors import LLMError

logger = logging.getLogger(__name__)


class ClaudePlatformClient:
    """
    Platform-side LLM client implementing PlatformLLMClient Protocol.

    Supports single key or multiple keys (round-robin rotation).
    Includes asyncio.Semaphore for concurrency control and automatic
    retry on rate limit errors.
    """

    def __init__(
        self,
        api_key: str | list[str],
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 4096,
        base_url: str | None = None,
        max_concurrent: int | None = None,
    ):
        keys = api_key if isinstance(api_key, list) else [api_key]
        client_kwargs: dict[str, Any] = {}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._clients = [
            anthropic.AsyncAnthropic(api_key=k, **client_kwargs)
            for k in keys
        ]
        self._cycle = itertools.cycle(range(len(self._clients)))
        self._model = model
        self._max_tokens = max_tokens

        # Default concurrency: 10 per key
        per_key = int(os.getenv("TOWOW_LLM_MAX_CONCURRENT_PER_KEY", "10"))
        concurrency = max_concurrent or (per_key * len(keys))
        self._semaphore = asyncio.Semaphore(concurrency)

        logger.info(
            "ClaudePlatformClient: %d key(s), max_concurrent=%d, base_url=%s",
            len(keys), concurrency, base_url or "default",
        )

    def _next_client(self) -> anthropic.AsyncAnthropic:
        idx = next(self._cycle)
        return self._clients[idx]

    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        async with self._semaphore:
            return await self._do_chat(messages, system_prompt, tools)

    async def _do_chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str],
        tools: Optional[list[dict[str, Any]]],
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = tools

        client = self._next_client()
        try:
            response = await client.messages.create(**kwargs)
            return self._parse_response(response)

        except anthropic.RateLimitError as e:
            logger.warning("Rate limit hit, switching key and retrying: %s", e)
            await asyncio.sleep(2)
            # Retry with next key
            client = self._next_client()
            try:
                response = await client.messages.create(**kwargs)
                return self._parse_response(response)
            except anthropic.APIError as retry_e:
                raise LLMError(f"LLM call failed after retry: {retry_e}") from retry_e

        except anthropic.APIError as e:
            logger.error("Platform LLM API error: %s", e)
            raise LLMError(f"Platform LLM call failed: {e}") from e

    def _parse_response(self, response: Any) -> dict[str, Any]:
        """Parse Anthropic API response into our standard format."""
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "name": block.name,
                    "arguments": block.input,
                    "id": block.id,
                })

        content = "".join(text_parts) if text_parts else None

        return {
            "content": content,
            "tool_calls": tool_calls if tool_calls else None,
            "stop_reason": response.stop_reason,
        }
