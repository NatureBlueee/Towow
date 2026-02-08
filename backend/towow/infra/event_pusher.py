"""
WebSocketEventPusher — Pushes negotiation events via WebSocket.

Wraps the existing WebSocketManager from backend/websocket_manager.py
to implement the EventPusher Protocol.
"""

from __future__ import annotations

import logging
from typing import Any

from towow.core.events import NegotiationEvent

logger = logging.getLogger(__name__)


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
