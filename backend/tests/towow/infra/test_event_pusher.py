"""Tests for WebSocketEventPusher."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from towow.core.events import EventType, NegotiationEvent
from towow.infra.event_pusher import WebSocketEventPusher


@pytest.fixture
def mock_ws_manager():
    manager = AsyncMock()
    manager.broadcast_to_channel = AsyncMock(return_value=3)
    return manager


@pytest.fixture
def pusher(mock_ws_manager):
    return WebSocketEventPusher(mock_ws_manager)


class TestPush:
    @pytest.mark.asyncio
    async def test_pushes_to_correct_channel(self, pusher, mock_ws_manager):
        event = NegotiationEvent(
            event_type=EventType.FORMULATION_READY,
            negotiation_id="neg_001",
            data={"raw_intent": "test", "formulated_text": "test"},
        )

        await pusher.push(event)

        mock_ws_manager.broadcast_to_channel.assert_awaited_once()
        call_args = mock_ws_manager.broadcast_to_channel.call_args
        assert call_args[0][0] == "negotiation:neg_001"

    @pytest.mark.asyncio
    async def test_sends_event_dict(self, pusher, mock_ws_manager):
        event = NegotiationEvent(
            event_type=EventType.OFFER_RECEIVED,
            negotiation_id="neg_002",
            data={"agent_id": "a1", "content": "I can help"},
        )

        await pusher.push(event)

        call_args = mock_ws_manager.broadcast_to_channel.call_args
        message = call_args[0][1]
        assert message["event_type"] == "offer.received"
        assert message["negotiation_id"] == "neg_002"
        assert message["data"]["agent_id"] == "a1"


class TestPushMany:
    @pytest.mark.asyncio
    async def test_pushes_all_events(self, pusher, mock_ws_manager):
        events = [
            NegotiationEvent(
                event_type=EventType.OFFER_RECEIVED,
                negotiation_id="neg_003",
                data={"agent_id": f"a{i}"},
            )
            for i in range(3)
        ]

        await pusher.push_many(events)

        assert mock_ws_manager.broadcast_to_channel.await_count == 3
