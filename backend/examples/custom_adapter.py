#!/usr/bin/env python3
"""
Towow SDK — Custom Adapter Example

Shows how to create a custom adapter for any LLM provider.
Adapters are the client-side LLM interface — each agent may use
a different model provider (OpenAI, Ollama, local model, etc.).

Usage:
    python examples/custom_adapter.py
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, Optional

from towow import BaseAdapter


# ---------------------------------------------------------------------------
# 1. Implement BaseAdapter for your LLM provider
# ---------------------------------------------------------------------------
class OpenAIAdapter(BaseAdapter):
    """
    Example adapter for OpenAI GPT models.

    In production, replace the mock implementation with real API calls.
    """

    def __init__(self, api_key: str, agent_profiles: dict[str, dict]):
        self._api_key = api_key
        self._profiles = agent_profiles
        # In production: self._client = openai.AsyncOpenAI(api_key=api_key)

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        """Return the agent's profile data for projection."""
        profile = self._profiles.get(agent_id)
        if profile is None:
            raise ValueError(f"Unknown agent: {agent_id}")
        return profile

    async def chat(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send a chat request to the agent's model."""
        profile = self._profiles.get(agent_id, {})

        # In production, call the real OpenAI API:
        #
        # msgs = []
        # if system_prompt:
        #     msgs.append({"role": "system", "content": system_prompt})
        # msgs.extend(messages)
        #
        # response = await self._client.chat.completions.create(
        #     model="gpt-4",
        #     messages=msgs,
        # )
        # return response.choices[0].message.content

        # Mock response for demo
        return f"[{profile.get('name', agent_id)}] Response to: {messages[-1]['content'][:50]}"

    async def chat_stream(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming version — yields text chunks."""
        # In production: use stream=True with OpenAI API
        full_response = await self.chat(agent_id, messages, system_prompt)
        for word in full_response.split():
            yield word + " "


# ---------------------------------------------------------------------------
# 2. Use with EngineBuilder
# ---------------------------------------------------------------------------
async def demo():
    adapter = OpenAIAdapter(
        api_key="sk-fake",
        agent_profiles={
            "alice": {"name": "Alice", "role": "Designer", "skills": ["Figma", "UX"]},
            "bob": {"name": "Bob", "role": "Developer", "skills": ["Python", "React"]},
        },
    )

    # Verify it works
    profile = await adapter.get_profile("alice")
    print(f"Alice's profile: {profile}")

    reply = await adapter.chat("alice", [{"role": "user", "content": "What can you do?"}])
    print(f"Alice's reply: {reply}")

    # Check Protocol conformance
    from towow import ProfileDataSource
    print(f"\nConforms to ProfileDataSource Protocol: {isinstance(adapter, ProfileDataSource)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
