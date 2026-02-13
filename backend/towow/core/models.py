"""
Core data models for the negotiation system.

These are the fundamental data structures shared across all modules.
They define WHAT the system works with, not HOW it processes them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ============ ID Generation ============

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}_{uid}" if prefix else uid


# ============ Agent Identity ============

class AgentType(str, Enum):
    EDGE = "edge"
    SERVICE = "service"


class SourceType(str, Enum):
    SECONDME = "secondme"
    CLAUDE = "claude"
    TEMPLATE = "template"
    CUSTOM = "custom"


@dataclass
class AgentIdentity:
    """
    An agent's identity in the network.

    V1: One person = one Edge Agent. Fields parent_id and agent_type
    are reserved for future multi-persona support.
    """
    agent_id: str
    display_name: str
    source_type: SourceType
    agent_type: AgentType = AgentType.EDGE
    parent_id: Optional[str] = None
    scene_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============ Scene ============

class AccessPolicy(str, Enum):
    OPEN = "open"
    INVITE = "invite"


class SceneStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class SceneDefinition:
    """
    A scene is an organized negotiation space.

    Scenes are the business entry point — each scene collects participants
    and provides a bounded broadcast space for negotiations.
    """
    scene_id: str
    name: str
    description: str
    organizer_id: str
    expected_responders: int = 10  # k* parameter
    access_policy: AccessPolicy = AccessPolicy.OPEN
    status: SceneStatus = SceneStatus.ACTIVE
    agent_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============ Negotiation Session ============

class NegotiationState(str, Enum):
    """
    Negotiation lifecycle states.

    The state machine is NOT purely linear — Center tool calls
    create loops (⑥→⑦→⑥). States reflect where we are in the
    overall flow, not individual Center turns.
    """
    CREATED = "created"                     # Session created, waiting for formulation
    FORMULATING = "formulating"             # Formulation in progress (client-side)
    FORMULATED = "formulated"               # Formulation done, waiting for user confirm
    ENCODING = "encoding"                   # Encoding demand + resonance detection
    OFFERING = "offering"                   # Parallel offer generation in progress
    BARRIER_WAITING = "barrier_waiting"     # Waiting for all offers (barrier)
    SYNTHESIZING = "synthesizing"           # Center is synthesizing (may loop)
    COMPLETED = "completed"                 # Negotiation complete with plan output


class AgentState(str, Enum):
    ACTIVE = "active"
    REPLIED = "replied"
    EXITED = "exited"


@dataclass
class AgentParticipant:
    """An agent participating in a negotiation."""
    agent_id: str
    display_name: str
    resonance_score: float = 0.0
    state: AgentState = AgentState.ACTIVE
    offer: Optional[Offer] = None


@dataclass
class Offer:
    """An offer from an agent responding to a demand."""
    agent_id: str
    content: str
    capabilities: list[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DemandSnapshot:
    """Snapshot of a demand at negotiation start time (snapshot isolation)."""
    raw_intent: str
    formulated_text: Optional[str] = None
    user_id: Optional[str] = None
    scene_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NegotiationSession:
    """
    The core negotiation unit — self-contained, recursive, composable.

    A session captures everything about one negotiation: the demand,
    participants, offers, center decisions, and trace. Sessions operate
    on snapshots (principle 0.11).
    """
    negotiation_id: str
    demand: DemandSnapshot
    state: NegotiationState = NegotiationState.CREATED
    participants: list[AgentParticipant] = field(default_factory=list)
    center_rounds: int = 0
    max_center_rounds: int = 1
    plan_output: Optional[str] = None
    plan_json: Optional[dict] = None
    parent_negotiation_id: Optional[str] = None  # For sub-negotiations (recursion)
    depth: int = 0                                # Recursion depth (0 = top-level)
    sub_session_ids: list[str] = field(default_factory=list)  # Child negotiation IDs
    trace: Optional[TraceChain] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    event_history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def active_participants(self) -> list[AgentParticipant]:
        return [p for p in self.participants if p.state == AgentState.ACTIVE]

    @property
    def pending_participants(self) -> list[AgentParticipant]:
        return [p for p in self.participants if p.state == AgentState.ACTIVE]

    @property
    def collected_offers(self) -> list[Offer]:
        return [p.offer for p in self.participants if p.offer is not None]

    @property
    def is_barrier_met(self) -> bool:
        """All participants have either replied or exited."""
        return all(
            p.state in (AgentState.REPLIED, AgentState.EXITED)
            for p in self.participants
        )

    @property
    def tools_restricted(self) -> bool:
        """After max rounds, only output_plan is allowed."""
        return self.center_rounds >= self.max_center_rounds


# ============ Trace Chain ============

@dataclass
class TraceEntry:
    """A single entry in the trace chain."""
    step: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[float] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceChain:
    """
    Complete trace of a negotiation — structured JSON log.

    Every step's input, output, timing, and LLM call info is recorded.
    Output as complete JSON when negotiation ends.
    """
    negotiation_id: str
    entries: list[TraceEntry] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def add_entry(self, step: str, **kwargs) -> TraceEntry:
        entry = TraceEntry(step=step, **kwargs)
        self.entries.append(entry)
        return entry

    def to_dict(self) -> dict[str, Any]:
        return {
            "negotiation_id": self.negotiation_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "entries": [
                {
                    "step": e.step,
                    "timestamp": e.timestamp.isoformat(),
                    "duration_ms": e.duration_ms,
                    "input_summary": e.input_summary,
                    "output_summary": e.output_summary,
                    "metadata": e.metadata,
                }
                for e in self.entries
            ],
        }
