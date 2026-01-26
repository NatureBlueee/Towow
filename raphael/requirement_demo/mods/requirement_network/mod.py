"""
Network-level Requirement Network mod for OpenAgents.

This mod enables a requirement-driven workflow with:
- User agents submitting requirements in natural language
- Automatic channel creation for each requirement
- Agent registry with admin-only access
- Admin agent invitation of relevant agents
- Coordinator task distribution and response handling
"""

import logging
import uuid
import time
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add local mod directory to path for imports
_mod_dir = Path(__file__).parent
if str(_mod_dir) not in sys.path:
    sys.path.insert(0, str(_mod_dir))

from openagents.core.base_mod import BaseMod, mod_event_handler
from openagents.models.event import Event
from openagents.models.event_response import EventResponse
from requirement_messages import (
    AgentRegistryEntry,
    RequirementChannel,
    RequirementSubmitMessage,
    TaskRespondMessage,
)

logger = logging.getLogger(__name__)


class RequirementNetworkMod(BaseMod):
    """Network-level mod for requirement-driven workflows.

    This mod provides:
    - Agent registry with capabilities and agent cards
    - Automatic channel creation when requirements are submitted
    - Admin-only registry access
    - Event notifications for channel creation, invitations, and tasks
    """

    def __init__(self, mod_name: str = "requirement_network"):
        """Initialize the requirement network mod.

        Args:
            mod_name: Name for the mod (default: "requirement_network")
        """
        super().__init__(mod_name=mod_name)

        # Agent registry: agent_id -> AgentRegistryEntry
        self.agent_registry: Dict[str, AgentRegistryEntry] = {}

        # Requirement channels: channel_id -> RequirementChannel
        self.requirement_channels: Dict[str, RequirementChannel] = {}

        # Track pending invitations: channel_id -> set of pending agent_ids
        self.pending_invitations: Dict[str, set] = {}

        # Track task assignments: task_id -> {channel_id, agent_id, status}
        self.task_assignments: Dict[str, Dict[str, Any]] = {}

        # Configuration
        self.admin_group = "admin"
        self.channel_prefix = "req"

        logger.info("RequirementNetworkMod initialized")

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update mod configuration."""
        super().update_config(config)

        # Update specific config values
        if "admin_group" in config:
            self.admin_group = config["admin_group"]
        if "channel_prefix" in config:
            self.channel_prefix = config["channel_prefix"]

        logger.info(f"RequirementNetworkMod config updated: admin_group={self.admin_group}")

    def _is_admin(self, agent_id: str) -> bool:
        """Check if an agent belongs to the admin group.

        Args:
            agent_id: The agent ID to check

        Returns:
            bool: True if the agent is an admin
        """
        if self.network and hasattr(self.network, "topology"):
            agent_group = self.network.topology.agent_group_membership.get(agent_id)
            return agent_group == self.admin_group
        return False

    def _generate_channel_id(self, requirement_id: str) -> str:
        """Generate a unique channel ID for a requirement."""
        return f"{self.channel_prefix}_{requirement_id}"

    def _generate_requirement_id(self) -> str:
        """Generate a unique requirement ID."""
        return uuid.uuid4().hex[:8]

    async def _create_messaging_channel(
        self, channel_id: str, description: str, creator_id: str
    ) -> bool:
        """Create a channel in the messaging mod.

        Args:
            channel_id: The channel ID to create
            description: Channel description
            creator_id: ID of the agent creating the channel

        Returns:
            bool: True if channel was created successfully
        """
        # Create channel via the messaging mod's event
        create_event = Event(
            event_name="thread.channel.create",
            source_id=f"mod:{self.mod_name}",
            payload={
                "channel_name": channel_id,
                "description": description,
                "private": True,
                "authorized_agents": [creator_id],
            },
            relevant_mod="openagents.mods.workspace.messaging",
        )

        try:
            await self.send_event(create_event)
            logger.info(f"Created messaging channel: {channel_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create messaging channel {channel_id}: {e}")
            return False

    @mod_event_handler("requirement_network.requirement.submit")
    async def _handle_requirement_submit(self, event: Event) -> Optional[EventResponse]:
        """Handle a requirement submission from a user agent.

        Creates a dedicated channel and emits channel_created event.

        Args:
            event: The requirement submit event

        Returns:
            EventResponse with the created channel info
        """
        try:
            # Validate the event
            RequirementSubmitMessage.validate(event)
        except ValueError as e:
            logger.warning(f"Invalid requirement submit: {e}")
            return EventResponse(
                success=False,
                message=str(e),
                data={"error": "validation_error"},
            )

        requirement_text = RequirementSubmitMessage.get_requirement_text(event)
        metadata = RequirementSubmitMessage.get_metadata(event)
        creator_id = event.source_id

        # Generate IDs
        requirement_id = self._generate_requirement_id()
        channel_id = self._generate_channel_id(requirement_id)

        # Create the requirement channel record
        requirement_channel = RequirementChannel(
            channel_id=channel_id,
            requirement_id=requirement_id,
            requirement_text=requirement_text,
            creator_agent_id=creator_id,
            status="pending",
            created_at=time.time(),
            metadata=metadata,
        )

        # Store the channel
        self.requirement_channels[channel_id] = requirement_channel

        # Initialize pending invitations set
        self.pending_invitations[channel_id] = set()

        # Create the messaging channel
        await self._create_messaging_channel(
            channel_id=channel_id,
            description=f"Requirement: {requirement_text[:100]}...",
            creator_id=creator_id,
        )

        logger.info(
            f"Requirement submitted: {requirement_id} by {creator_id} - '{requirement_text[:50]}...'"
        )

        # Emit channel_created notification (broadcast to all agents)
        channel_created_event = Event(
            event_name="requirement_network.channel_created",
            source_id=f"mod:{self.mod_name}",
            destination_id="agent:broadcast",  # Broadcast to all agents
            payload={
                "channel_id": channel_id,
                "requirement_id": requirement_id,
                "requirement_text": requirement_text,
                "creator_id": creator_id,
                "metadata": metadata,
                "created_timestamp": requirement_channel.created_at,
            },
            relevant_mod="openagents.mods.workspace.requirement_network",
        )
        logger.info(f"Broadcasting channel_created event for {channel_id}")
        await self.send_event(channel_created_event)

        return EventResponse(
            success=True,
            message=f"Requirement submitted, channel created: {channel_id}",
            data={
                "channel_id": channel_id,
                "requirement_id": requirement_id,
            },
        )

    @mod_event_handler("requirement_network.registry.register")
    async def _handle_registry_register(self, event: Event) -> Optional[EventResponse]:
        """Handle agent registration with capabilities.

        Args:
            event: The registry register event

        Returns:
            EventResponse confirming registration
        """
        agent_id = event.source_id
        payload = event.payload or {}

        capabilities = payload.get("capabilities", {})
        agent_card = payload.get("agent_card")

        # Get agent group if available
        agent_group = None
        if self.network and hasattr(self.network, "topology"):
            agent_group = self.network.topology.agent_group_membership.get(agent_id)

        # Create or update registry entry
        entry = AgentRegistryEntry(
            agent_id=agent_id,
            agent_group=agent_group,
            capabilities=capabilities,
            agent_card=agent_card,
            registered_at=time.time(),
        )

        self.agent_registry[agent_id] = entry

        logger.info(
            f"Agent registered in requirement_network registry: {agent_id} "
            f"(group: {agent_group}, capabilities: {list(capabilities.keys())})"
        )

        return EventResponse(
            success=True,
            message=f"Agent {agent_id} registered successfully",
            data={"agent_id": agent_id},
        )

    @mod_event_handler("requirement_network.registry.read")
    async def _handle_registry_read(self, event: Event) -> Optional[EventResponse]:
        """Handle registry read request (admin-only).

        Args:
            event: The registry read event

        Returns:
            EventResponse with registry data (if admin) or error
        """
        agent_id = event.source_id

        # Check admin permission
        if not self._is_admin(agent_id):
            logger.warning(f"Non-admin agent {agent_id} attempted to read registry")
            return EventResponse(
                success=False,
                message="Access denied: Admin permission required to read registry",
                data={"error": "unauthorized"},
            )

        payload = event.payload or {}
        filter_criteria = payload.get("filter", {})

        # Build registry data
        agents_data = []
        for entry in self.agent_registry.values():
            # Apply filter if provided
            if filter_criteria:
                # Simple filter by capabilities
                if "skills" in filter_criteria:
                    required_skills = set(filter_criteria["skills"])
                    agent_skills = set(entry.capabilities.get("skills", []))
                    if not required_skills.intersection(agent_skills):
                        continue

            agents_data.append({
                "agent_id": entry.agent_id,
                "agent_group": entry.agent_group,
                "capabilities": entry.capabilities,
                "agent_card": entry.agent_card,
                "registered_at": entry.registered_at,
            })

        logger.info(f"Admin {agent_id} read registry: {len(agents_data)} agents")

        return EventResponse(
            success=True,
            message=f"Registry read successful: {len(agents_data)} agents",
            data={"agents": agents_data},
        )

    @mod_event_handler("requirement_network.agent.invite")
    async def _handle_agent_invite(self, event: Event) -> Optional[EventResponse]:
        """Handle agent invitation to a requirement channel.

        Args:
            event: The agent invite event

        Returns:
            EventResponse confirming invitation
        """
        agent_id = event.source_id
        payload = event.payload or {}

        channel_id = payload.get("channel_id")
        agent_ids = payload.get("agent_ids", [])

        # Validate channel exists
        if channel_id not in self.requirement_channels:
            return EventResponse(
                success=False,
                message=f"Channel not found: {channel_id}",
                data={"error": "channel_not_found"},
            )

        requirement_channel = self.requirement_channels[channel_id]

        # Add agents to invited list
        for invited_id in agent_ids:
            if invited_id not in requirement_channel.invited_agents:
                requirement_channel.invited_agents.append(invited_id)

            # Track pending invitation
            self.pending_invitations[channel_id].add(invited_id)

        logger.info(
            f"Agents invited to {channel_id}: {agent_ids} (by {agent_id})"
        )

        # Emit invitation notification for each agent
        for invited_id in agent_ids:
            invite_notification = Event(
                event_name="requirement_network.notification.agent_invited",
                source_id=f"mod:{self.mod_name}",
                destination_id=invited_id,
                payload={
                    "channel_id": channel_id,
                    "requirement_id": requirement_channel.requirement_id,
                    "requirement_text": requirement_channel.requirement_text,
                    "invited_by": agent_id,
                },
                relevant_mod="openagents.mods.workspace.requirement_network",
            )
            await self.send_event(invite_notification)

        return EventResponse(
            success=True,
            message=f"Invited {len(agent_ids)} agents to channel {channel_id}",
            data={
                "channel_id": channel_id,
                "invited_agents": agent_ids,
            },
        )

    @mod_event_handler("requirement_network.channel.join")
    async def _handle_channel_join(self, event: Event) -> Optional[EventResponse]:
        """Handle agent joining a requirement channel.

        Args:
            event: The channel join event

        Returns:
            EventResponse confirming join
        """
        agent_id = event.source_id
        payload = event.payload or {}
        channel_id = payload.get("channel_id")

        if channel_id not in self.requirement_channels:
            return EventResponse(
                success=False,
                message=f"Channel not found: {channel_id}",
                data={"error": "channel_not_found"},
            )

        # Remove from pending if present
        if channel_id in self.pending_invitations:
            self.pending_invitations[channel_id].discard(agent_id)

            # Check if all invitations are complete
            if len(self.pending_invitations[channel_id]) == 0:
                requirement_channel = self.requirement_channels[channel_id]

                # Emit invitations_complete notification (broadcast to all agents)
                complete_event = Event(
                    event_name="requirement_network.invitations_complete",
                    source_id=f"mod:{self.mod_name}",
                    destination_id="agent:broadcast",
                    payload={
                        "channel_id": channel_id,
                        "requirement_id": requirement_channel.requirement_id,
                        "requirement_text": requirement_channel.requirement_text,
                        "invited_agents": requirement_channel.invited_agents,
                    },
                    relevant_mod="openagents.mods.workspace.requirement_network",
                )
                logger.info(f"Broadcasting invitations_complete event for {channel_id}")
                await self.send_event(complete_event)

                logger.info(f"All invitations complete for channel {channel_id}")

        logger.info(f"Agent {agent_id} joined channel {channel_id}")

        return EventResponse(
            success=True,
            message=f"Joined channel {channel_id}",
            data={"channel_id": channel_id},
        )

    @mod_event_handler("requirement_network.invitations.complete")
    async def _handle_invitations_complete_signal(self, event: Event) -> Optional[EventResponse]:
        """Handle explicit signal that all invitations are complete.

        This allows the admin to signal completion even if not all agents have joined.

        Args:
            event: The invitations complete signal event

        Returns:
            EventResponse confirming the signal
        """
        payload = event.payload or {}
        channel_id = payload.get("channel_id")

        if channel_id not in self.requirement_channels:
            return EventResponse(
                success=False,
                message=f"Channel not found: {channel_id}",
                data={"error": "channel_not_found"},
            )

        requirement_channel = self.requirement_channels[channel_id]

        # Clear pending invitations
        self.pending_invitations[channel_id] = set()

        # Emit invitations_complete notification (broadcast to all agents)
        complete_event = Event(
            event_name="requirement_network.invitations_complete",
            source_id=f"mod:{self.mod_name}",
            destination_id="agent:broadcast",
            payload={
                "channel_id": channel_id,
                "requirement_id": requirement_channel.requirement_id,
                "requirement_text": requirement_channel.requirement_text,
                "invited_agents": requirement_channel.invited_agents,
            },
            relevant_mod="openagents.mods.workspace.requirement_network",
        )
        logger.info(f"Broadcasting invitations_complete event for {channel_id}")
        await self.send_event(complete_event)

        return EventResponse(
            success=True,
            message=f"Invitations complete for {channel_id}",
            data={"channel_id": channel_id},
        )

    @mod_event_handler("requirement_network.task.distribute")
    async def _handle_task_distribute(self, event: Event) -> Optional[EventResponse]:
        """Handle task distribution to an agent.

        Args:
            event: The task distribute event

        Returns:
            EventResponse confirming distribution
        """
        payload = event.payload or {}

        channel_id = payload.get("channel_id")
        agent_id = payload.get("agent_id")
        task_id = payload.get("task_id")
        task = payload.get("task", {})

        if channel_id not in self.requirement_channels:
            return EventResponse(
                success=False,
                message=f"Channel not found: {channel_id}",
                data={"error": "channel_not_found"},
            )

        # Track task assignment
        self.task_assignments[task_id] = {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "task": task,
            "status": "pending",
            "distributed_at": time.time(),
        }

        # Update channel status
        self.requirement_channels[channel_id].status = "in_progress"

        # Send notification to the assigned agent
        task_notification = Event(
            event_name="requirement_network.notification.task_distributed",
            source_id=f"mod:{self.mod_name}",
            destination_id=agent_id,
            payload={
                "channel_id": channel_id,
                "task_id": task_id,
                "task": task,
                "distributed_by": event.source_id,
            },
            relevant_mod="openagents.mods.workspace.requirement_network",
        )
        await self.send_event(task_notification)

        logger.info(f"Task {task_id} distributed to {agent_id} in channel {channel_id}")

        return EventResponse(
            success=True,
            message=f"Task {task_id} distributed to {agent_id}",
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "channel_id": channel_id,
            },
        )

    @mod_event_handler("requirement_network.task.respond")
    async def _handle_task_respond(self, event: Event) -> Optional[EventResponse]:
        """Handle task response from an agent.

        Args:
            event: The task response event

        Returns:
            EventResponse confirming the response
        """
        try:
            TaskRespondMessage.validate(event)
        except ValueError as e:
            return EventResponse(
                success=False,
                message=str(e),
                data={"error": "validation_error"},
            )

        payload = event.payload or {}

        task_id = payload.get("task_id")
        channel_id = payload.get("channel_id")
        response_type = payload.get("response_type")
        content = payload.get("content", {})
        agent_id = event.source_id

        # Update task assignment
        if task_id in self.task_assignments:
            self.task_assignments[task_id]["status"] = response_type
            self.task_assignments[task_id]["response"] = content
            self.task_assignments[task_id]["responded_at"] = time.time()

        # Emit task response notification (broadcast to coordinator and others)
        response_notification = Event(
            event_name="requirement_network.notification.task_response",
            source_id=f"mod:{self.mod_name}",
            destination_id="agent:broadcast",
            payload={
                "channel_id": channel_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "response_type": response_type,
                "content": content,
            },
            relevant_mod="openagents.mods.workspace.requirement_network",
        )
        await self.send_event(response_notification)

        logger.info(
            f"Task {task_id} response from {agent_id}: {response_type}"
        )

        # If response is accept, notify the user
        if response_type == "accept" and channel_id in self.requirement_channels:
            requirement_channel = self.requirement_channels[channel_id]

            user_notification = Event(
                event_name="requirement_network.notification.user_update",
                source_id=f"mod:{self.mod_name}",
                destination_id=requirement_channel.creator_agent_id,
                payload={
                    "channel_id": channel_id,
                    "update_type": "task_accepted",
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "content": content,
                },
                relevant_mod="openagents.mods.workspace.requirement_network",
            )
            await self.send_event(user_notification)

        return EventResponse(
            success=True,
            message=f"Task response recorded: {response_type}",
            data={
                "task_id": task_id,
                "response_type": response_type,
            },
        )

    @mod_event_handler("requirement_network.channel.get_info")
    async def _handle_channel_get_info(self, event: Event) -> Optional[EventResponse]:
        """Get information about a requirement channel.

        Args:
            event: The channel info request event

        Returns:
            EventResponse with channel information
        """
        payload = event.payload or {}
        channel_id = payload.get("channel_id")

        if channel_id not in self.requirement_channels:
            return EventResponse(
                success=False,
                message=f"Channel not found: {channel_id}",
                data={"error": "channel_not_found"},
            )

        channel = self.requirement_channels[channel_id]

        return EventResponse(
            success=True,
            message="Channel info retrieved",
            data={
                "channel_id": channel.channel_id,
                "requirement_id": channel.requirement_id,
                "requirement_text": channel.requirement_text,
                "creator_agent_id": channel.creator_agent_id,
                "invited_agents": channel.invited_agents,
                "status": channel.status,
                "created_at": channel.created_at,
                "metadata": channel.metadata,
            },
        )

    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the mod."""
        return {
            "agent_registry_count": len(self.agent_registry),
            "requirement_channels_count": len(self.requirement_channels),
            "active_tasks": len([t for t in self.task_assignments.values() if t["status"] == "pending"]),
        }
