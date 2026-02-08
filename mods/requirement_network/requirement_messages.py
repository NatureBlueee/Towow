"""
Requirement Network specific message models for OpenAgents.

Defines Pydantic models and validators for requirement_network events.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from openagents.models.event import Event


@dataclass
class AgentRegistryEntry:
    """An entry in the agent registry."""

    agent_id: str
    agent_group: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    agent_card: Optional[Dict[str, Any]] = None
    registered_at: float = 0.0


@dataclass
class RequirementChannel:
    """Represents a requirement channel with its metadata."""

    channel_id: str
    requirement_id: str
    requirement_text: str
    creator_agent_id: str
    invited_agents: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, cancelled
    created_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequirementSubmitMessage:
    """Validator and helper for requirement submit events."""

    @classmethod
    def validate(cls, event: Event) -> Event:
        """Validate that event.payload has required fields.

        Args:
            event: Event to validate

        Returns:
            Event: The validated event

        Raises:
            ValueError: If validation fails
        """
        payload = event.payload or {}

        if "requirement_text" not in payload:
            raise ValueError("Requirement submit must have 'requirement_text' in payload")

        if not isinstance(payload["requirement_text"], str):
            raise ValueError("requirement_text must be a string")

        if payload["requirement_text"].strip() == "":
            raise ValueError("requirement_text cannot be empty")

        return event

    @classmethod
    def create(
        cls,
        requirement_text: str,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Event:
        """Create a properly formatted requirement submit Event.

        Args:
            requirement_text: The requirement in natural language
            source_id: ID of the agent submitting the requirement
            metadata: Optional metadata (priority, deadline, tags, etc.)
            **kwargs: Additional fields for the Event

        Returns:
            Event: Properly formatted requirement submit event
        """
        payload = {
            "requirement_text": requirement_text,
            "metadata": metadata or {},
        }

        return Event(
            event_name="requirement_network.requirement.submit",
            source_id=source_id,
            payload=payload,
            relevant_mod="openagents.mods.workspace.requirement_network",
            **kwargs,
        )

    @staticmethod
    def get_requirement_text(event: Event) -> str:
        """Extract requirement text from event payload."""
        return event.payload.get("requirement_text", "") if event.payload else ""

    @staticmethod
    def get_metadata(event: Event) -> Dict[str, Any]:
        """Extract metadata from event payload."""
        return event.payload.get("metadata", {}) if event.payload else {}


class RegistryRegisterMessage:
    """Validator and helper for agent registry registration events."""

    @classmethod
    def create(
        cls,
        source_id: str,
        capabilities: Optional[Dict[str, Any]] = None,
        agent_card: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Event:
        """Create a registry registration Event.

        Args:
            source_id: ID of the agent registering
            capabilities: Agent capabilities (skills, specialties, etc.)
            agent_card: Agent profile/card information
            **kwargs: Additional fields for the Event

        Returns:
            Event: Properly formatted registry register event
        """
        payload = {
            "capabilities": capabilities or {},
            "agent_card": agent_card,
        }

        return Event(
            event_name="requirement_network.registry.register",
            source_id=source_id,
            payload=payload,
            relevant_mod="openagents.mods.workspace.requirement_network",
            **kwargs,
        )


class RegistryReadMessage:
    """Validator and helper for agent registry read events."""

    @classmethod
    def create(
        cls,
        source_id: str,
        filter_criteria: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Event:
        """Create a registry read Event.

        Args:
            source_id: ID of the agent reading the registry (must be admin)
            filter_criteria: Optional filter criteria for the query
            **kwargs: Additional fields for the Event

        Returns:
            Event: Properly formatted registry read event
        """
        payload = {
            "filter": filter_criteria or {},
        }

        return Event(
            event_name="requirement_network.registry.read",
            source_id=source_id,
            payload=payload,
            relevant_mod="openagents.mods.workspace.requirement_network",
            **kwargs,
        )


class AgentInviteMessage:
    """Validator and helper for agent invite events."""

    @classmethod
    def create(
        cls,
        source_id: str,
        channel_id: str,
        agent_ids: List[str],
        **kwargs,
    ) -> Event:
        """Create an agent invite Event.

        Args:
            source_id: ID of the admin agent inviting
            channel_id: The requirement channel to invite agents to
            agent_ids: List of agent IDs to invite
            **kwargs: Additional fields for the Event

        Returns:
            Event: Properly formatted agent invite event
        """
        payload = {
            "channel_id": channel_id,
            "agent_ids": agent_ids,
        }

        return Event(
            event_name="requirement_network.agent.invite",
            source_id=source_id,
            payload=payload,
            relevant_mod="openagents.mods.workspace.requirement_network",
            **kwargs,
        )


class TaskDistributeMessage:
    """Validator and helper for task distribution events."""

    @classmethod
    def create(
        cls,
        source_id: str,
        channel_id: str,
        agent_id: str,
        task: Dict[str, Any],
        task_id: Optional[str] = None,
        **kwargs,
    ) -> Event:
        """Create a task distribute Event.

        Args:
            source_id: ID of the coordinator distributing the task
            channel_id: The requirement channel
            agent_id: The agent to assign the task to
            task: The task details
            task_id: Optional task ID (auto-generated if not provided)
            **kwargs: Additional fields for the Event

        Returns:
            Event: Properly formatted task distribute event
        """
        import uuid

        payload = {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "task_id": task_id or str(uuid.uuid4()),
            "task": task,
        }

        return Event(
            event_name="requirement_network.task.distribute",
            source_id=source_id,
            destination_id=agent_id,
            payload=payload,
            relevant_mod="openagents.mods.workspace.requirement_network",
            **kwargs,
        )


class TaskRespondMessage:
    """Validator and helper for task response events."""

    RESPONSE_TYPES = ["accept", "reject", "propose"]

    @classmethod
    def validate(cls, event: Event) -> Event:
        """Validate task response event."""
        payload = event.payload or {}

        if "response_type" not in payload:
            raise ValueError("Task response must have 'response_type' in payload")

        if payload["response_type"] not in cls.RESPONSE_TYPES:
            raise ValueError(f"response_type must be one of: {cls.RESPONSE_TYPES}")

        if "channel_id" not in payload:
            raise ValueError("Task response must have 'channel_id' in payload")

        if "task_id" not in payload:
            raise ValueError("Task response must have 'task_id' in payload")

        return event

    @classmethod
    def create(
        cls,
        source_id: str,
        channel_id: str,
        task_id: str,
        response_type: str,
        content: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Event:
        """Create a task response Event.

        Args:
            source_id: ID of the agent responding
            channel_id: The requirement channel
            task_id: The task being responded to
            response_type: Type of response (accept, reject, propose)
            content: Response content (message, reason, alternative, etc.)
            **kwargs: Additional fields for the Event

        Returns:
            Event: Properly formatted task response event
        """
        if response_type not in cls.RESPONSE_TYPES:
            raise ValueError(f"response_type must be one of: {cls.RESPONSE_TYPES}")

        payload = {
            "channel_id": channel_id,
            "task_id": task_id,
            "response_type": response_type,
            "content": content or {},
        }

        return Event(
            event_name="requirement_network.task.respond",
            source_id=source_id,
            payload=payload,
            relevant_mod="openagents.mods.workspace.requirement_network",
            **kwargs,
        )

    @staticmethod
    def get_response_type(event: Event) -> str:
        """Extract response type from event payload."""
        return event.payload.get("response_type", "") if event.payload else ""
