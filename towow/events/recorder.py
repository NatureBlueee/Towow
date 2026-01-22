"""
Event Recorder

Records all events and supports subscription for real-time streaming.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class EventRecord:
    """Event record data structure."""
    event_id: str
    event_type: str
    timestamp: str
    channel_id: Optional[str]
    demand_id: Optional[str]
    payload: Dict


class EventRecorder:
    """
    Event Recorder for ToWow.

    Features:
    1. Records all events (keeps last 1000 in memory)
    2. Supports querying history by channel/demand
    3. Supports subscribing to new events for SSE streaming
    """

    MAX_EVENTS = 1000
    MAX_SUBSCRIBERS = 1000
    SUBSCRIBER_TIMEOUT = 300  # 5 minutes inactive timeout

    def __init__(self):
        self.events: deque = deque(maxlen=self.MAX_EVENTS)
        self.subscribers: Set[asyncio.Queue] = set()
        self._subscriber_last_active: Dict[asyncio.Queue, float] = {}
        self._lock = asyncio.Lock()

    async def record(self, event: Dict) -> None:
        """
        Record an event.

        Args:
            event: Event dict with event_id, event_type, timestamp, payload
        """
        async with self._lock:
            record = EventRecord(
                event_id=event.get("event_id", ""),
                event_type=event.get("event_type", ""),
                timestamp=event.get("timestamp", datetime.utcnow().isoformat()),
                channel_id=event.get("payload", {}).get("channel_id"),
                demand_id=event.get("payload", {}).get("demand_id"),
                payload=event.get("payload", {})
            )
            self.events.append(record)

            # Notify all subscribers and update their last active time
            now = time.time()
            for queue in list(self.subscribers):
                try:
                    queue.put_nowait(event)
                    self._subscriber_last_active[queue] = now
                except asyncio.QueueFull:
                    logger.warning("Subscriber queue full, dropping event")

    def subscribe(self) -> Optional[asyncio.Queue]:
        """
        Subscribe to event stream.

        Returns:
            Queue that will receive new events, or None if max subscribers reached
        """
        if len(self.subscribers) >= self.MAX_SUBSCRIBERS:
            logger.warning(
                f"Max subscribers ({self.MAX_SUBSCRIBERS}) reached, "
                "rejecting new subscription"
            )
            return None

        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(queue)
        self._subscriber_last_active[queue] = time.time()
        logger.debug(f"New subscriber added, total: {len(self.subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unsubscribe from event stream.

        Args:
            queue: The queue to remove from subscribers
        """
        self.subscribers.discard(queue)
        self._subscriber_last_active.pop(queue, None)
        logger.debug(f"Subscriber removed, total: {len(self.subscribers)}")

    async def cleanup_stale_subscribers(self) -> int:
        """
        Clean up subscribers that have been inactive for too long.

        Returns:
            Number of subscribers cleaned up
        """
        now = time.time()
        stale = [
            q for q, last_active in self._subscriber_last_active.items()
            if now - last_active > self.SUBSCRIBER_TIMEOUT
        ]
        for queue in stale:
            self.unsubscribe(queue)
            logger.info(
                f"Cleaned up stale subscriber, remaining: {len(self.subscribers)}"
            )
        return len(stale)

    def get_by_channel(self, channel_id: str, limit: int = 50) -> List[Dict]:
        """
        Get history events for a specific channel.

        Args:
            channel_id: Channel ID to filter by
            limit: Maximum number of events to return

        Returns:
            List of event dicts, oldest first
        """
        result = []
        for record in reversed(self.events):
            if record.channel_id and channel_id in record.channel_id:
                result.append({
                    "event_id": record.event_id,
                    "event_type": record.event_type,
                    "timestamp": record.timestamp,
                    "payload": record.payload
                })
                if len(result) >= limit:
                    break
        return list(reversed(result))

    def get_by_demand(self, demand_id: str, limit: int = 50) -> List[Dict]:
        """
        Get history events for a specific demand.

        Args:
            demand_id: Demand ID to filter by
            limit: Maximum number of events to return

        Returns:
            List of event dicts, oldest first
        """
        result = []
        for record in reversed(self.events):
            if record.demand_id == demand_id:
                result.append({
                    "event_id": record.event_id,
                    "event_type": record.event_type,
                    "timestamp": record.timestamp,
                    "payload": record.payload
                })
                if len(result) >= limit:
                    break
        return list(reversed(result))

    def get_after(self, event_id: str, limit: int = 50) -> List[Dict]:
        """
        Get events after a specific event ID (for reconnection support).

        Args:
            event_id: Event ID to start after
            limit: Maximum number of events to return

        Returns:
            List of event dicts after the specified event
        """
        result = []
        found = False
        for record in self.events:
            if found:
                result.append({
                    "event_id": record.event_id,
                    "event_type": record.event_type,
                    "timestamp": record.timestamp,
                    "payload": record.payload
                })
                if len(result) >= limit:
                    break
            elif record.event_id == event_id:
                found = True
        return result

    def get_all(self, limit: int = 50) -> List[Dict]:
        """
        Get all recent events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of most recent event dicts
        """
        result = []
        for record in reversed(self.events):
            result.append({
                "event_id": record.event_id,
                "event_type": record.event_type,
                "timestamp": record.timestamp,
                "payload": record.payload
            })
            if len(result) >= limit:
                break
        return list(reversed(result))


# Global event recorder instance
event_recorder = EventRecorder()
