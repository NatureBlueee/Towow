"""Database models for ToWow platform."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base

if TYPE_CHECKING:
    pass


class DemandStatus(str, Enum):
    """Status of a demand."""

    DRAFT = "draft"  # Initial state
    PUBLISHED = "published"  # Actively seeking agents
    MATCHING = "matching"  # In negotiation process
    MATCHED = "matched"  # Successfully matched with agent(s)
    COMPLETED = "completed"  # Demand fulfilled
    CANCELLED = "cancelled"  # Demand cancelled


class ResponseStatus(str, Enum):
    """Status of an agent response."""

    PENDING = "pending"  # Awaiting review
    ACCEPTED = "accepted"  # Response accepted
    REJECTED = "rejected"  # Response rejected
    WITHDRAWN = "withdrawn"  # Agent withdrew response


class ChannelStatus(str, Enum):
    """Status of a collaboration channel."""

    ACTIVE = "active"  # Channel is active
    PAUSED = "paused"  # Temporarily paused
    COMPLETED = "completed"  # Collaboration completed
    CLOSED = "closed"  # Channel closed


class AgentProfile(Base):
    """Agent profile representing an AI agent's public profile."""

    __tablename__ = "agent_profiles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Capabilities and skills as JSONB
    capabilities: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Pricing and availability info
    pricing_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Agent configuration
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Metadata
    is_active: Mapped[bool] = mapped_column(default=True)
    rating: Mapped[Optional[float]] = mapped_column(nullable=True)
    total_collaborations: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    responses: Mapped[List["AgentResponse"]] = relationship(
        "AgentResponse", back_populates="agent", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_agent_profiles_agent_type", "agent_type"),
        Index("ix_agent_profiles_is_active", "is_active"),
    )


class Demand(Base):
    """Demand model representing a user's requirement."""

    __tablename__ = "demands"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # User who created the demand
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Demand details as JSONB
    requirements: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Budget and timeline
    budget: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), default=DemandStatus.DRAFT.value
    )

    # Additional metadata
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    responses: Mapped[List["AgentResponse"]] = relationship(
        "AgentResponse", back_populates="demand", lazy="selectin"
    )
    channels: Mapped[List["CollaborationChannel"]] = relationship(
        "CollaborationChannel", back_populates="demand", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_demands_user_id", "user_id"),
        Index("ix_demands_status", "status"),
        Index("ix_demands_created_at", "created_at"),
    )


class CollaborationChannel(Base):
    """Channel for collaboration between user and agent(s)."""

    __tablename__ = "collaboration_channels"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign keys
    demand_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("demands.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Participants (user + agents)
    participants: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Channel status
    status: Mapped[str] = mapped_column(
        String(50), default=ChannelStatus.ACTIVE.value
    )

    # Negotiation/collaboration context
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Message history summary (full history may be in separate storage)
    message_count: Mapped[int] = mapped_column(default=0)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Additional settings
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    demand: Mapped["Demand"] = relationship(
        "Demand", back_populates="channels"
    )

    __table_args__ = (
        Index("ix_collaboration_channels_demand_id", "demand_id"),
        Index("ix_collaboration_channels_status", "status"),
    )


class AgentResponse(Base):
    """Agent's response to a demand."""

    __tablename__ = "agent_responses"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Foreign keys
    demand_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("demands.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agent_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Response content
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Proposal details
    proposal: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=ResponseStatus.PENDING.value
    )

    # Scoring/ranking
    relevance_score: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Additional metadata
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    demand: Mapped["Demand"] = relationship(
        "Demand", back_populates="responses"
    )
    agent: Mapped["AgentProfile"] = relationship(
        "AgentProfile", back_populates="responses"
    )

    __table_args__ = (
        Index("ix_agent_responses_demand_id", "demand_id"),
        Index("ix_agent_responses_agent_id", "agent_id"),
        Index("ix_agent_responses_status", "status"),
    )
