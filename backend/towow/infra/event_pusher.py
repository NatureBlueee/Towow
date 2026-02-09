"""
EventPusher implementations — push negotiation events to the product layer.

Provides three implementations:
- WebSocketEventPusher: broadcasts via WebSocket (production)
- NullEventPusher: silently discards (headless / testing)
- LoggingEventPusher: logs events (debugging / CI)
"""

from __future__ import annotations

import logging
from typing import Any

from towow.core.events import NegotiationEvent

logger = logging.getLogger(__name__)


class NullEventPusher:
    """EventPusher that silently discards all events.

    Use for headless mode (notebooks, CI, scripts) where no
    WebSocket or event transport is needed.
    """

    async def push(self, event: NegotiationEvent) -> None:
        pass

    async def push_many(self, events: list[NegotiationEvent]) -> None:
        pass


class LoggingEventPusher:
    """EventPusher that logs events at INFO level.

    Use for debugging or CI where you want to see events
    without a WebSocket server.
    """

    async def push(self, event: NegotiationEvent) -> None:
        logger.info(
            "Event [%s] %s: %s",
            event.negotiation_id,
            event.event_type.value,
            {k: str(v)[:100] for k, v in event.data.items()},
        )

    async def push_many(self, events: list[NegotiationEvent]) -> None:
        for event in events:
            await self.push(event)


class WebSocketEventPusher:
    """
    EventPusher implementation that broadcasts events via WebSocket.

    Channel naming: negotiation:{negotiation_id}
    """

    def __init__(self, ws_manager: Any):
        """
        Args:
            ws_manager: A WebSocketManager instance from backend/websocket_manager.py
        """
        self._ws_manager = ws_manager

    def _channel_name(self, negotiation_id: str) -> str:
        return f"negotiation:{negotiation_id}"

    async def push(self, event: NegotiationEvent) -> None:
        """Push a single event to the negotiation's WebSocket channel."""
        channel = self._channel_name(event.negotiation_id)
        message = event.to_dict()
        sent = await self._ws_manager.broadcast_to_channel(channel, message)
        logger.debug(
            f"Pushed event {event.event_type.value} to {channel} "
            f"({sent} connections)"
        )

    async def push_many(self, events: list[NegotiationEvent]) -> None:
        """Push multiple events."""
        for event in events:
            await self.push(event)
