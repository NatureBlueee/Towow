"""
Agent-level Requirement Network adapter for OpenAgents.

This adapter provides tools for agents to interact with the requirement_network mod:
- Submit requirements
- Register capabilities
- Read registry (admin-only)
- Invite agents
- Distribute tasks
- Respond to tasks
"""

import logging
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add local mod directory to path for imports
_mod_dir = Path(__file__).parent
if str(_mod_dir) not in sys.path:
    sys.path.insert(0, str(_mod_dir))

from openagents.core.base_mod_adapter import BaseModAdapter
from openagents.models.event import Event, EventVisibility
from openagents.models.tool import AgentTool
from requirement_messages import (
    RequirementSubmitMessage,
    RegistryRegisterMessage,
    RegistryReadMessage,
    AgentInviteMessage,
    TaskDistributeMessage,
    TaskRespondMessage,
)

logger = logging.getLogger(__name__)


class RequirementNetworkAdapter(BaseModAdapter):
    """Agent-level adapter for requirement_network mod.

    This adapter provides tools for agents to:
    - Submit requirements in natural language
    - Register their capabilities with the network
    - Read the agent registry (admin-only)
    - Invite agents to requirement channels
    - Distribute tasks to agents
    - Respond to distributed tasks
    """

    def __init__(self):
        """Initialize the requirement network adapter."""
        super().__init__(mod_name="requirement_network")

        # Track pending requests for response handling
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.completed_requests: Dict[str, Dict[str, Any]] = {}

    def initialize(self) -> bool:
        """Initialize the adapter."""
        logger.info(f"Initializing RequirementNetworkAdapter for agent {self.agent_id}")
        return True

    def shutdown(self) -> bool:
        """Shutdown the adapter."""
        logger.info(f"Shutting down RequirementNetworkAdapter for agent {self.agent_id}")
        return True

    async def submit_requirement(
        self,
        requirement_text: str,
        priority: Optional[str] = None,
        deadline: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Submit a new requirement in natural language.

        Args:
            requirement_text: The requirement description in natural language
            priority: Optional priority level (low, medium, high)
            deadline: Optional deadline string
            tags: Optional list of tags for categorization

        Returns:
            Dict with channel_id and requirement_id if successful
        """
        if not self.agent_client:
            logger.error("Cannot submit requirement: agent_client is None")
            return {"success": False, "error": "not_connected"}

        metadata = {}
        if priority:
            metadata["priority"] = priority
        if deadline:
            metadata["deadline"] = deadline
        if tags:
            metadata["tags"] = tags

        event = RequirementSubmitMessage.create(
            requirement_text=requirement_text,
            source_id=self.agent_id,
            metadata=metadata,
        )

        # Store pending request
        request_id = event.event_id
        self.pending_requests[request_id] = {
            "action": "submit_requirement",
            "timestamp": event.timestamp,
        }

        try:
            response = await self.agent_client.send_event(event)

            if response and response.success:
                logger.info(f"Requirement submitted: {response.data}")
                # Handle case where response.data is None (mod not installed on network)
                if response.data is None:
                    logger.warning("Response data is None - requirement_network mod may not be installed on the network")
                    return {"success": False, "error": "requirement_network mod not available"}
                return {
                    "success": True,
                    "channel_id": response.data.get("channel_id"),
                    "requirement_id": response.data.get("requirement_id"),
                }
            else:
                error_msg = response.message if response else "No response"
                logger.error(f"Failed to submit requirement: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Error submitting requirement: {e}")
            return {"success": False, "error": str(e)}
        finally:
            self.pending_requests.pop(request_id, None)

    async def register_capabilities(
        self,
        skills: Optional[List[str]] = None,
        specialties: Optional[List[str]] = None,
        agent_card: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register agent capabilities with the network.

        Args:
            skills: List of skills (e.g., ["python", "design", "analysis"])
            specialties: List of specialties (e.g., ["web-development", "data-science"])
            agent_card: Full agent profile/card with additional info

        Returns:
            Dict indicating success or failure
        """
        if not self.agent_client:
            logger.error("Cannot register capabilities: agent_client is None")
            return {"success": False, "error": "not_connected"}

        capabilities = {}
        if skills:
            capabilities["skills"] = skills
        if specialties:
            capabilities["specialties"] = specialties

        event = RegistryRegisterMessage.create(
            source_id=self.agent_id,
            capabilities=capabilities,
            agent_card=agent_card,
        )

        try:
            response = await self.agent_client.send_event(event)

            if response and response.success:
                logger.info(f"Capabilities registered for {self.agent_id}")
                return {"success": True, "agent_id": self.agent_id}
            else:
                error_msg = response.message if response else "No response"
                logger.error(f"Failed to register capabilities: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Error registering capabilities: {e}")
            return {"success": False, "error": str(e)}

    async def read_agent_registry(
        self,
        filter_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Read the agent registry (admin-only).

        Args:
            filter_skills: Optional list of skills to filter by

        Returns:
            Dict with list of registered agents or error
        """
        if not self.agent_client:
            logger.error("Cannot read registry: agent_client is None")
            return {"success": False, "error": "not_connected"}

        filter_criteria = {}
        if filter_skills:
            filter_criteria["skills"] = filter_skills

        event = RegistryReadMessage.create(
            source_id=self.agent_id,
            filter_criteria=filter_criteria,
        )

        try:
            response = await self.agent_client.send_event(event)

            if response and response.success:
                agents = response.data.get("agents", [])
                logger.info(f"Registry read: {len(agents)} agents")
                return {"success": True, "agents": agents}
            else:
                error_msg = response.message if response else "No response"
                logger.error(f"Failed to read registry: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Error reading registry: {e}")
            return {"success": False, "error": str(e)}

    async def invite_agents(
        self,
        channel_id: str,
        agent_ids: List[str],
    ) -> Dict[str, Any]:
        """Invite agents to a requirement channel.

        Args:
            channel_id: The requirement channel ID
            agent_ids: List of agent IDs to invite

        Returns:
            Dict indicating success or failure
        """
        if not self.agent_client:
            logger.error("Cannot invite agents: agent_client is None")
            return {"success": False, "error": "not_connected"}

        event = AgentInviteMessage.create(
            source_id=self.agent_id,
            channel_id=channel_id,
            agent_ids=agent_ids,
        )

        try:
            response = await self.agent_client.send_event(event)

            if response and response.success:
                logger.info(f"Invited {len(agent_ids)} agents to {channel_id}")
                return {
                    "success": True,
                    "channel_id": channel_id,
                    "invited_agents": agent_ids,
                }
            else:
                error_msg = response.message if response else "No response"
                logger.error(f"Failed to invite agents: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Error inviting agents: {e}")
            return {"success": False, "error": str(e)}

    async def signal_invitations_complete(
        self,
        channel_id: str,
    ) -> Dict[str, Any]:
        """Signal that all invitations are complete for a channel.

        Args:
            channel_id: The requirement channel ID

        Returns:
            Dict indicating success or failure
        """
        if not self.agent_client:
            logger.error("Cannot signal invitations complete: agent_client is None")
            return {"success": False, "error": "not_connected"}

        event = Event(
            event_name="requirement_network.invitations.complete",
            source_id=self.agent_id,
            payload={"channel_id": channel_id},
            relevant_mod="openagents.mods.workspace.requirement_network",
        )

        try:
            response = await self.agent_client.send_event(event)

            if response and response.success:
                logger.info(f"Invitations marked complete for {channel_id}")
                return {"success": True, "channel_id": channel_id}
            else:
                error_msg = response.message if response else "No response"
                logger.error(f"Failed to signal invitations complete: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Error signaling invitations complete: {e}")
            return {"success": False, "error": str(e)}

    async def join_channel(
        self,
        channel_id: str,
    ) -> Dict[str, Any]:
        """Join a requirement channel.

        Args:
            channel_id: The requirement channel ID to join

        Returns:
            Dict indicating success or failure
        """
        if not self.agent_client:
            logger.error("Cannot join channel: agent_client is None")
            return {"success": False, "error": "not_connected"}

        event = Event(
            event_name="requirement_network.channel.join",
            source_id=self.agent_id,
            payload={"channel_id": channel_id},
            relevant_mod="openagents.mods.workspace.requirement_network",
        )

        try:
            response = await self.agent_client.send_event(event)

            if response and response.success:
                logger.info(f"Joined channel {channel_id}")
                return {"success": True, "channel_id": channel_id}
            else:
                error_msg = response.message if response else "No response"
                logger.error(f"Failed to join channel: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Error joining channel: {e}")
            return {"success": False, "error": str(e)}

    async def get_channel_info(
        self,
        channel_id: str,
    ) -> Dict[str, Any]:
        """Get information about a requirement channel.

        Args:
            channel_id: The requirement channel ID

        Returns:
            Dict with channel information or error
        """
        if not self.agent_client:
            logger.error("Cannot get channel info: agent_client is None")
            return {"success": False, "error": "not_connected"}

        event = Event(
            event_name="requirement_network.channel.get_info",
            source_id=self.agent_id,
            payload={"channel_id": channel_id},
            relevant_mod="openagents.mods.workspace.requirement_network",
        )

        try:
            response = await self.agent_client.send_event(event)

            if response and response.success:
                logger.info(f"Got info for channel {channel_id}")
                return {"success": True, **response.data}
            else:
                error_msg = response.message if response else "No response"
                logger.error(f"Failed to get channel info: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return {"success": False, "error": str(e)}

    async def distribute_task(
        self,
        channel_id: str,
        agent_id: str,
        task_description: str,
        task_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Distribute a task to an agent.

        Args:
            channel_id: The requirement channel ID
            agent_id: The agent to assign the task to
            task_description: Description of the task
            task_details: Optional additional task details

        Returns:
            Dict with task_id if successful
        """
        if not self.agent_client:
            logger.error("Cannot distribute task: agent_client is None")
            return {"success": False, "error": "not_connected"}

        task = {
            "description": task_description,
            **(task_details or {}),
        }

        event = TaskDistributeMessage.create(
            source_id=self.agent_id,
            channel_id=channel_id,
            agent_id=agent_id,
            task=task,
        )

        task_id = event.payload.get("task_id")

        try:
            response = await self.agent_client.send_event(event)

            if response and response.success:
                logger.info(f"Task {task_id} distributed to {agent_id}")
                return {
                    "success": True,
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "channel_id": channel_id,
                }
            else:
                error_msg = response.message if response else "No response"
                logger.error(f"Failed to distribute task: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Error distributing task: {e}")
            return {"success": False, "error": str(e)}

    async def respond_to_task(
        self,
        channel_id: str,
        task_id: str,
        response_type: str,
        message: Optional[str] = None,
        reason: Optional[str] = None,
        alternative: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Respond to a distributed task.

        Args:
            channel_id: The requirement channel ID
            task_id: The task ID to respond to
            response_type: Type of response (accept, reject, propose)
            message: Optional message (for accept)
            reason: Optional reason (for reject)
            alternative: Optional alternative proposal (for propose)

        Returns:
            Dict indicating success or failure
        """
        if not self.agent_client:
            logger.error("Cannot respond to task: agent_client is None")
            return {"success": False, "error": "not_connected"}

        content = {}
        if message:
            content["message"] = message
        if reason:
            content["reason"] = reason
        if alternative:
            content["alternative"] = alternative

        event = TaskRespondMessage.create(
            source_id=self.agent_id,
            channel_id=channel_id,
            task_id=task_id,
            response_type=response_type,
            content=content,
        )

        try:
            response = await self.agent_client.send_event(event)

            if response and response.success:
                logger.info(f"Task {task_id} response sent: {response_type}")
                return {
                    "success": True,
                    "task_id": task_id,
                    "response_type": response_type,
                }
            else:
                error_msg = response.message if response else "No response"
                logger.error(f"Failed to respond to task: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Error responding to task: {e}")
            return {"success": False, "error": str(e)}

    def get_tools(self) -> List[AgentTool]:
        """Get the tools provided by this adapter.

        Returns:
            List of AgentTool definitions
        """
        tools = []

        # Tool 1: Submit requirement
        tools.append(AgentTool(
            name="submit_requirement",
            description="Submit a new requirement in natural language. Creates a dedicated channel for the requirement.",
            input_schema={
                "type": "object",
                "properties": {
                    "requirement_text": {
                        "type": "string",
                        "description": "The requirement description in natural language",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Optional priority level",
                    },
                    "deadline": {
                        "type": "string",
                        "description": "Optional deadline (e.g., '2025-02-01')",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for categorization",
                    },
                },
                "required": ["requirement_text"],
            },
            func=self.submit_requirement,
        ))

        # Tool 2: Register capabilities
        tools.append(AgentTool(
            name="register_capabilities",
            description="Register your capabilities with the network for discovery by the admin agent.",
            input_schema={
                "type": "object",
                "properties": {
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of skills (e.g., ['python', 'design'])",
                    },
                    "specialties": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of specialties (e.g., ['web-development'])",
                    },
                    "agent_card": {
                        "type": "object",
                        "description": "Optional full agent profile/card",
                    },
                },
                "required": [],
            },
            func=self.register_capabilities,
        ))

        # Tool 3: Read registry (admin-only)
        tools.append(AgentTool(
            name="read_agent_registry",
            description="Read the agent registry to find agents with specific capabilities. Admin permission required.",
            input_schema={
                "type": "object",
                "properties": {
                    "filter_skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of skills to filter by",
                    },
                },
                "required": [],
            },
            func=self.read_agent_registry,
        ))

        # Tool 4: Invite agents
        tools.append(AgentTool(
            name="invite_agents",
            description="Invite agents to a requirement channel.",
            input_schema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The requirement channel ID",
                    },
                    "agent_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of agent IDs to invite",
                    },
                },
                "required": ["channel_id", "agent_ids"],
            },
            func=self.invite_agents,
        ))

        # Tool 5: Signal invitations complete
        tools.append(AgentTool(
            name="signal_invitations_complete",
            description="Signal that all invitations are complete for a channel, triggering the coordinator.",
            input_schema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The requirement channel ID",
                    },
                },
                "required": ["channel_id"],
            },
            func=self.signal_invitations_complete,
        ))

        # Tool 6: Join channel
        tools.append(AgentTool(
            name="join_requirement_channel",
            description="Join a requirement channel after being invited.",
            input_schema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The requirement channel ID to join",
                    },
                },
                "required": ["channel_id"],
            },
            func=self.join_channel,
        ))

        # Tool 7: Get channel info
        tools.append(AgentTool(
            name="get_channel_info",
            description="Get information about a requirement channel.",
            input_schema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The requirement channel ID",
                    },
                },
                "required": ["channel_id"],
            },
            func=self.get_channel_info,
        ))

        # Tool 8: Distribute task
        tools.append(AgentTool(
            name="distribute_task",
            description="Distribute a task to an agent in the channel.",
            input_schema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The requirement channel ID",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "The agent to assign the task to",
                    },
                    "task_description": {
                        "type": "string",
                        "description": "Description of the task",
                    },
                    "task_details": {
                        "type": "object",
                        "description": "Optional additional task details",
                    },
                },
                "required": ["channel_id", "agent_id", "task_description"],
            },
            func=self.distribute_task,
        ))

        # Tool 9: Respond to task
        tools.append(AgentTool(
            name="respond_to_task",
            description="Respond to a distributed task (accept, reject, or propose alternative).",
            input_schema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The requirement channel ID",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "The task ID to respond to",
                    },
                    "response_type": {
                        "type": "string",
                        "enum": ["accept", "reject", "propose"],
                        "description": "Type of response",
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional message (for accept)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason (for reject)",
                    },
                    "alternative": {
                        "type": "string",
                        "description": "Optional alternative proposal (for propose)",
                    },
                },
                "required": ["channel_id", "task_id", "response_type"],
            },
            func=self.respond_to_task,
        ))

        return tools
