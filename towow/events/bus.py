"""Event Bus implementation for ToWow.

Simple async event bus for internal event broadcasting.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Awaitable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data structure."""
    event_id: str
    event_type: str
    timestamp: str
    payload: Dict[str, Any]

    @classmethod
    def create(cls, event_type: str, payload: Dict[str, Any]) -> "Event":
        """Create a new event."""
        return cls(
            event_id=f"evt-{uuid4().hex[:8]}",
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            payload=payload
        )


# Handler can be sync or async
EventHandler = Union[Callable[[Event], Awaitable[None]], Callable[[Event], None]]


class EventBus:
    """
    Simple async event bus for internal event broadcasting.

    Supports:
    - Publishing events to all subscribers
    - Subscribing to specific event types
    - Wildcard subscriptions (e.g., "towow.demand.*")
    """

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._history: List[Event] = []
        self._max_history = 1000
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Event type pattern (supports wildcards like "towow.demand.*")
            handler: Async function to call when event is published
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"已订阅事件: {event_type}")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def publish(self, event: Dict[str, Any] | Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event dict or Event object
        """
        if isinstance(event, dict):
            event = Event(
                event_id=event.get("event_id", f"evt-{uuid4().hex[:8]}"),
                event_type=event.get("event_type", "unknown"),
                timestamp=event.get("timestamp", datetime.utcnow().isoformat()),
                payload=event.get("payload", {})
            )

        # Store in history
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        logger.info(f"事件已发布: {event.event_type} ({event.event_id})")

        # Find matching handlers
        handlers_to_call = []

        for pattern, handlers in self._handlers.items():
            if self._matches(pattern, event.event_type):
                handlers_to_call.extend(handlers)

        # Call all handlers concurrently
        if handlers_to_call:
            async def safe_call(handler, evt):
                """Safely call handler, supporting both sync and async."""
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(evt)
                    else:
                        handler(evt)
                except Exception as e:
                    logger.error(f"事件 {evt.event_type} 处理器错误: {e}")

            tasks = [safe_call(handler, event) for handler in handlers_to_call]
            await asyncio.gather(*tasks, return_exceptions=True)

    def _matches(self, pattern: str, event_type: str) -> bool:
        """Check if event type matches pattern (supports wildcards)."""
        if pattern == "*":
            return True

        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_type.startswith(prefix + ".")

        return pattern == event_type

    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get event history, optionally filtered by type."""
        events = self._history

        if event_type:
            events = [e for e in events if self._matches(event_type, e.event_type)]

        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# Global event bus instance
event_bus = EventBus()
