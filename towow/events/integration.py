"""
Event Recording Integration

Integrates the event bus with the event recorder for automatic recording.
"""
from __future__ import annotations

import logging
from typing import Dict, Union

from events.bus import Event, event_bus
from events.recorder import event_recorder

logger = logging.getLogger(__name__)


async def record_towow_event(event: Union[Event, Dict]) -> None:
    """
    Record ToWow event to the recorder.

    Args:
        event: Event object or dict to record
    """
    if isinstance(event, Event):
        event_dict = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "payload": event.payload
        }
    else:
        event_dict = event

    await event_recorder.record(event_dict)


def setup_event_recording() -> None:
    """
    Set up event recording.

    Subscribes to all towow.* events and records them to the event recorder.
    """
    # Subscribe to all towow events using wildcard
    event_bus.subscribe("towow.*", record_towow_event)

    # Also subscribe to specific event types for explicit handling
    event_types = [
        "towow.demand.broadcast",
        "towow.demand.understood",
        "towow.filter.completed",
        "towow.offer.submitted",
        "towow.proposal.distributed",
        "towow.proposal.feedback",
        "towow.proposal.finalized",
        "towow.negotiation.failed",
        "towow.subnet.triggered",
        "towow.subnet.completed",
        "towow.gap.identified"
    ]

    for event_type in event_types:
        event_bus.subscribe(event_type, record_towow_event)

    logger.info("Event recording integration set up successfully")
