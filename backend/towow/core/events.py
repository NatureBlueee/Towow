"""
Event definitions — the 9 event types pushed from protocol layer to product layer.

Events follow a uniform JSON structure. The protocol layer pushes ALL events;
the product layer decides what to display.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    """The 9 negotiation event types (V1 implements 7, reserves 2)."""
    FORMULATION_READY = "formulation.ready"
    RESONANCE_ACTIVATED = "resonance.activated"
    OFFER_RECEIVED = "offer.received"
    BARRIER_COMPLETE = "barrier.complete"
    CENTER_TOOL_CALL = "center.tool_call"
    PLAN_READY = "plan.ready"
    SUB_NEGOTIATION_STARTED = "sub_negotiation.started"
    # V1 does not push these two:
    EXECUTION_PROGRESS = "execution.progress"
    ECHO_RECEIVED = "echo.received"


@dataclass
class NegotiationEvent:
    """
    Uniform event structure pushed via WebSocket.

    All 9 event types share this outer structure.
    The `data` field varies by event type.
    """
    event_type: EventType
    negotiation_id: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "negotiation_id": self.negotiation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
            "data": self.data,
        }


# ============ Event factory functions ============

def formulation_ready(
    negotiation_id: str,
    raw_intent: str,
    formulated_text: str,
    enrichments: dict[str, Any] | None = None,
) -> NegotiationEvent:
    return NegotiationEvent(
        event_type=EventType.FORMULATION_READY,
        negotiation_id=negotiation_id,
        data={
            "raw_intent": raw_intent,
            "formulated_text": formulated_text,
            "enrichments": enrichments or {},
        },
    )


def resonance_activated(
    negotiation_id: str,
    activated_count: int,
    agents: list[dict[str, Any]],
) -> NegotiationEvent:
    return NegotiationEvent(
        event_type=EventType.RESONANCE_ACTIVATED,
        negotiation_id=negotiation_id,
        data={
            "activated_count": activated_count,
            "agents": agents,  # [{agent_id, display_name, resonance_score}]
        },
    )


def offer_received(
    negotiation_id: str,
    agent_id: str,
    display_name: str,
    content: str,
    capabilities: list[str] | None = None,
) -> NegotiationEvent:
    return NegotiationEvent(
        event_type=EventType.OFFER_RECEIVED,
        negotiation_id=negotiation_id,
        data={
            "agent_id": agent_id,
            "display_name": display_name,
            "content": content,
            "capabilities": capabilities or [],
        },
    )


def barrier_complete(
    negotiation_id: str,
    total_participants: int,
    offers_received: int,
    exited_count: int,
) -> NegotiationEvent:
    return NegotiationEvent(
        event_type=EventType.BARRIER_COMPLETE,
        negotiation_id=negotiation_id,
        data={
            "total_participants": total_participants,
            "offers_received": offers_received,
            "exited_count": exited_count,
        },
    )


def center_tool_call(
    negotiation_id: str,
    tool_name: str,
    tool_args: dict[str, Any],
    round_number: int,
) -> NegotiationEvent:
    return NegotiationEvent(
        event_type=EventType.CENTER_TOOL_CALL,
        negotiation_id=negotiation_id,
        data={
            "tool_name": tool_name,
            "tool_args": tool_args,
            "round_number": round_number,
        },
    )


def plan_ready(
    negotiation_id: str,
    plan_text: str,
    center_rounds: int,
    participating_agents: list[str],
) -> NegotiationEvent:
    return NegotiationEvent(
        event_type=EventType.PLAN_READY,
        negotiation_id=negotiation_id,
        data={
            "plan_text": plan_text,
            "center_rounds": center_rounds,
            "participating_agents": participating_agents,
        },
    )


def sub_negotiation_started(
    negotiation_id: str,
    sub_negotiation_id: str,
    gap_description: str,
) -> NegotiationEvent:
    return NegotiationEvent(
        event_type=EventType.SUB_NEGOTIATION_STARTED,
        negotiation_id=negotiation_id,
        data={
            "sub_negotiation_id": sub_negotiation_id,
            "gap_description": gap_description,
        },
    )
