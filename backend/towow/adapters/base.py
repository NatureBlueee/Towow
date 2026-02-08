"""
Abstract base for ProfileDataSource adapters.

Adapters are the client-side LLM interface — each user may have
a different model provider (SecondMe, Claude, etc.). Adapters abstract
away which model is used, exposing a uniform get_profile/chat/chat_stream.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    Abstract base class for ProfileDataSource adapters.

    Subclasses implement access to a specific LLM provider.
    All methods match the ProfileDataSource Protocol in core/protocols.py.
    """

    @abstractmethod
    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        """Get agent's profile data for projection."""
        ...

    @abstractmethod
    async def chat(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send a chat request. Returns the complete response text."""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming version of chat. Yields text chunks."""
        ...
