"""
SecondMeAdapter — Adapter wrapping the existing SecondMe OAuth2 client.

Routes chat requests through SecondMe's chat_stream API using
the existing SecondMeOAuth2Client from backend/oauth2_client.py.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Optional

from towow.core.errors import AdapterError

from .base import BaseAdapter

logger = logging.getLogger(__name__)


class SecondMeAdapter(BaseAdapter):
    """
    Client-side adapter for SecondMe users.

    Wraps SecondMeOAuth2Client to implement the ProfileDataSource Protocol.
    Requires an access_token for the user's SecondMe session.
    """

    def __init__(
        self,
        oauth2_client: Any,  # SecondMeOAuth2Client — avoids circular import
        access_token: str,
        profiles: dict[str, dict[str, Any]] | None = None,
    ):
        self._client = oauth2_client
        self._access_token = access_token
        self._profiles = profiles or {}

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        """Return stored profile data. V1 returns from in-memory store."""
        if agent_id in self._profiles:
            return self._profiles[agent_id]

        # Fallback: try to get user info from SecondMe
        try:
            user_info = await self._client.get_user_info(self._access_token)
            return {
                "agent_id": agent_id,
                "name": user_info.name,
                "bio": user_info.bio,
                "self_introduction": user_info.self_introduction,
            }
        except Exception as e:
            logger.warning(f"Failed to get profile from SecondMe for {agent_id}: {e}")
            return {"agent_id": agent_id}

    async def chat(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send chat via SecondMe, collect full response from stream."""
        chunks: list[str] = []
        async for chunk in self.chat_stream(agent_id, messages, system_prompt):
            chunks.append(chunk)
        return "".join(chunks)

    async def chat_stream(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat via SecondMe's chat_stream API, yielding text chunks."""
        try:
            async for event in self._client.chat_stream(
                access_token=self._access_token,
                messages=messages,
                system_prompt=system_prompt,
            ):
                if event.get("type") == "data":
                    content = event.get("content", "")
                    if content:
                        yield content
                elif event.get("type") == "done":
                    return

        except Exception as e:
            logger.error(f"SecondMe chat error for agent {agent_id}: {e}")
            raise AdapterError(f"SecondMe chat failed: {e}") from e
