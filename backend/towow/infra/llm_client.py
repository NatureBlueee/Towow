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
import time
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

    def _next_client(self) -> tuple[int, anthropic.AsyncAnthropic]:
        idx = next(self._cycle)
        return idx, self._clients[idx]

    def _key_label(self, idx: int) -> str:
        """Return safe label for logging (key index + last 4 chars)."""
        key = self._clients[idx].api_key
        return f"key[{idx}]...{key[-4:]}"

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

        msg_count = len(messages)
        tool_count = len(tools) if tools else 0
        idx, client = self._next_client()
        key_label = self._key_label(idx)

        logger.info("LLM call START | %s | model=%s | messages=%d | tools=%d | system=%s",
                     key_label, self._model, msg_count, tool_count,
                     "yes" if system_prompt else "no")
        t0 = time.monotonic()

        try:
            response = await client.messages.create(**kwargs)
            elapsed_ms = (time.monotonic() - t0) * 1000
            parsed = self._parse_response(response)

            tc = len(parsed["tool_calls"]) if parsed.get("tool_calls") else 0
            text_len = len(parsed["content"]) if parsed.get("content") else 0
            logger.info("LLM call OK    | %s | %.0fms | stop=%s | tool_calls=%d | text_len=%d",
                         key_label, elapsed_ms, parsed.get("stop_reason"), tc, text_len)
            return parsed

        except anthropic.RateLimitError as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.warning("LLM call RATE_LIMITED | %s | %.0fms | %s — switching key",
                           key_label, elapsed_ms, e)
            await asyncio.sleep(2)
            idx2, client2 = self._next_client()
            key_label2 = self._key_label(idx2)
            logger.info("LLM call RETRY | %s", key_label2)
            t1 = time.monotonic()
            try:
                response = await client2.messages.create(**kwargs)
                elapsed_ms2 = (time.monotonic() - t1) * 1000
                parsed = self._parse_response(response)
                tc = len(parsed["tool_calls"]) if parsed.get("tool_calls") else 0
                text_len = len(parsed["content"]) if parsed.get("content") else 0
                logger.info("LLM call OK    | %s | %.0fms | stop=%s | tool_calls=%d | text_len=%d",
                             key_label2, elapsed_ms2, parsed.get("stop_reason"), tc, text_len)
                return parsed
            except anthropic.APIError as retry_e:
                elapsed_ms2 = (time.monotonic() - t1) * 1000
                logger.error("LLM call FAIL  | %s | %.0fms | %s", key_label2, elapsed_ms2, retry_e)
                raise LLMError(f"LLM call failed after retry: {retry_e}") from retry_e

        except anthropic.APIError as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.error("LLM call FAIL  | %s | %.0fms | %s", key_label, elapsed_ms, e)
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
