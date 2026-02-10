"""
SecondMeAdapter — Adapter wrapping the existing SecondMe OAuth2 client.

Routes chat requests through SecondMe's chat_stream API using
the existing SecondMeOAuth2Client from backend/oauth2_client.py.

Each instance represents ONE SecondMe user (one token = one Agent).
Profile is built from info + shades + softmemory on initialization.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Optional

from towow.core.errors import AdapterError

from .base import BaseAdapter

logger = logging.getLogger(__name__)


class SecondMeAdapter(BaseAdapter):
    """
    Client-side adapter for a single SecondMe user.

    Wraps SecondMeOAuth2Client to implement the ProfileDataSource Protocol.
    One adapter instance = one SecondMe user = one Agent in the network.

    Profile is built from SecondMe's info + shades + softmemory APIs
    via fetch_and_build_profile(). Chat requests route back to SecondMe.
    """

    def __init__(
        self,
        oauth2_client: Any,  # SecondMeOAuth2Client — avoids circular import
        access_token: str,
        agent_id: str | None = None,
        profile: dict[str, Any] | None = None,
    ):
        self._client = oauth2_client
        self._access_token = access_token
        self._agent_id = agent_id  # set after fetch_and_build_profile
        self._profile = profile  # set after fetch_and_build_profile

    @property
    def agent_id(self) -> str | None:
        return self._agent_id

    @property
    def profile(self) -> dict[str, Any] | None:
        return self._profile

    async def fetch_and_build_profile(self) -> dict[str, Any]:
        """
        Fetch full profile from SecondMe (info + shades + softmemory)
        and build a structured agent profile.

        Sets self._agent_id and self._profile.
        Returns the built profile dict.
        """
        # Lazy import to avoid circular dependency
        import sys
        oauth2_mod = sys.modules.get("oauth2_client")
        if oauth2_mod is None:
            # Try importing from backend package
            try:
                from oauth2_client import build_agent_profile
            except ImportError:
                # Fallback: define inline
                build_agent_profile = self._build_profile_fallback
        else:
            build_agent_profile = oauth2_mod.build_agent_profile

        # 1. Fetch user info (always available)
        try:
            user_info = await self._client.get_user_info(self._access_token)
        except Exception as e:
            logger.error(f"Failed to fetch user info: {e}")
            raise AdapterError(f"Cannot build profile: {e}") from e

        # 2. Fetch shades (optional — graceful fallback)
        shades = []
        try:
            shades = await self._client.get_shades(self._access_token)
        except Exception as e:
            logger.warning(f"Failed to fetch shades: {e}")

        # 3. Fetch soft memory (optional — graceful fallback)
        memories = []
        try:
            memories = await self._client.get_softmemory(self._access_token)
        except Exception as e:
            logger.warning(f"Failed to fetch soft memory: {e}")

        # 4. Build profile
        profile = build_agent_profile(user_info, shades, memories)

        self._agent_id = profile["agent_id"]
        self._profile = profile

        logger.info(
            f"Built SecondMe profile: name={profile.get('name')}, "
            f"shades={len(shades)}, memories={len(memories)}"
        )
        return profile

    @staticmethod
    def _build_profile_fallback(user_info, shades=None, memories=None):
        """Fallback profile builder if oauth2_client module not available."""
        return {
            "agent_id": user_info.open_id,
            "name": user_info.name or "Unknown",
            "bio": user_info.bio or "",
            "self_introduction": user_info.self_introduction or "",
            "source": "secondme",
            "shades": [{"name": s.name, "description": s.description} for s in (shades or [])],
            "memories": [{"category": m.category, "content": m.content} for m in (memories or [])],
        }

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        """Return the built profile. Fetches on demand if not yet built."""
        if self._profile and (agent_id == self._agent_id or not self._agent_id):
            return self._profile

        # Auto-build if not yet done
        if self._profile is None:
            await self.fetch_and_build_profile()
            if self._profile:
                return self._profile

        return {"agent_id": agent_id, "source": "secondme"}

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
