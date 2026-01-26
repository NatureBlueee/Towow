#!/usr/bin/env python3
"""
Designer Agent for Requirement Demo Network.

This Python-based agent handles design-related tasks:
1. Registers design capabilities when invited to a channel
2. Receives task assignments from the coordinator
3. Responds with accept/reject/propose based on task analysis
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add local mods folder to path for requirement_network adapter
_script_dir = Path(__file__).parent.parent
_mods_dir = _script_dir / "mods"
if _mods_dir.exists() and str(_mods_dir) not in sys.path:
    sys.path.insert(0, str(_mods_dir))

from openagents.agents.worker_agent import WorkerAgent, on_event
from openagents.models.event_context import EventContext
from requirement_network import RequirementNetworkAdapter
from openagents.mods.workspace.messaging import ThreadMessagingAgentAdapter

logger = logging.getLogger(__name__)


class DesignerAgent(WorkerAgent):
    """
    Designer agent that handles UI/UX design tasks.

    Capabilities:
    - Visual design and mockups
    - User interface layouts
    - User experience optimization
    - Responsive design
    - Design systems and style guides

    Workflow:
    1. Receive agent_invited event -> register capabilities, join channel
    2. Receive task_distributed event -> analyze and respond (accept/reject/propose)
    """

    default_agent_id = "designer"

    # Define designer's capabilities
    SKILLS = ["ui-design", "ux-design", "figma", "responsive-design", "prototyping"]
    SPECIALTIES = ["landing-pages", "web-apps", "mobile-design", "design-systems"]

    # Keywords that indicate design work
    DESIGN_KEYWORDS = [
        "design", "ui", "ux", "mockup", "wireframe", "visual", "layout",
        "interface", "figma", "prototype", "landing", "responsive", "style",
        "branding", "logo", "typography", "color", "icon", "illustration"
    ]

    # Keywords that indicate non-design work (should reject)
    NON_DESIGN_KEYWORDS = [
        "code", "implement", "develop", "programming", "api", "database",
        "backend", "server", "test", "debug", "deploy", "algorithm"
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize adapters
        self.requirement_adapter = RequirementNetworkAdapter()
        self.messaging_adapter = ThreadMessagingAgentAdapter()

        # Track joined channels
        self.joined_channels: set = set()

    async def on_startup(self):
        """Called after successful connection and setup."""
        # Bind adapters after client is initialized
        self.requirement_adapter.bind_client(self.client)
        self.requirement_adapter.bind_connector(self.client.connector)
        self.requirement_adapter.bind_agent(self.agent_id)

        self.messaging_adapter.bind_client(self.client)
        self.messaging_adapter.bind_connector(self.client.connector)
        self.messaging_adapter.bind_agent(self.agent_id)

        logger.info(f"Designer Agent '{self.client.agent_id}' started")
        logger.info(f"Skills: {self.SKILLS}")
        logger.info(f"Specialties: {self.SPECIALTIES}")

        # Register capabilities on startup
        await self._register_capabilities()

    async def _register_capabilities(self):
        """Register the designer's capabilities with the network."""
        logger.info("Registering design capabilities...")

        result = await self.requirement_adapter.register_capabilities(
            skills=self.SKILLS,
            specialties=self.SPECIALTIES,
        )

        if result.get("success"):
            logger.info("Successfully registered capabilities")
        else:
            logger.error(f"Failed to register capabilities: {result.get('error')}")

    def _analyze_task(self, task_description: str, task_type: str) -> Dict[str, Any]:
        """Analyze a task to determine appropriate response.

        Args:
            task_description: The task description
            task_type: The task type

        Returns:
            Dict with response_type and details
        """
        description_lower = task_description.lower()
        type_lower = task_type.lower()

        # Check if it's clearly design-related
        design_matches = sum(1 for kw in self.DESIGN_KEYWORDS if kw in description_lower)
        non_design_matches = sum(1 for kw in self.NON_DESIGN_KEYWORDS if kw in description_lower)

        # Also check task type
        if type_lower in ["design", "ui", "ux", "visual"]:
            design_matches += 3
        elif type_lower in ["development", "coding", "backend", "testing"]:
            non_design_matches += 3

        logger.info(f"Task analysis - design keywords: {design_matches}, non-design: {non_design_matches}")

        if design_matches > non_design_matches:
            # Accept the task
            return {
                "response_type": "accept",
                "message": self._generate_acceptance_message(task_description),
            }
        elif non_design_matches > design_matches:
            # Reject - not a design task
            return {
                "response_type": "reject",
                "reason": "This task appears to be outside my design expertise. "
                          "It seems more suited for a developer or other specialist.",
            }
        else:
            # Propose an alternative - maybe we can help with design aspects
            return {
                "response_type": "propose",
                "alternative": "I can help with the visual design aspects of this task, "
                              "including UI mockups, wireframes, and style guidelines. "
                              "The technical implementation would need a developer.",
                "message": "I notice this task has both design and technical components.",
            }

    def _generate_acceptance_message(self, task_description: str) -> str:
        """Generate an acceptance message with a brief plan.

        Args:
            task_description: The task description

        Returns:
            Acceptance message with plan
        """
        description_lower = task_description.lower()

        deliverables = []
        if any(kw in description_lower for kw in ["mockup", "visual", "ui"]):
            deliverables.append("UI mockups")
        if any(kw in description_lower for kw in ["wireframe", "layout", "structure"]):
            deliverables.append("wireframes")
        if any(kw in description_lower for kw in ["responsive", "mobile"]):
            deliverables.append("responsive designs")
        if any(kw in description_lower for kw in ["style", "brand", "guideline"]):
            deliverables.append("style guide")
        if any(kw in description_lower for kw in ["prototype", "interactive"]):
            deliverables.append("interactive prototype")

        if not deliverables:
            deliverables = ["UI mockups", "wireframes"]

        return (
            f"I'll work on this design task. My plan:\n"
            f"1. Review requirements and gather inspiration\n"
            f"2. Create initial concepts and wireframes\n"
            f"3. Develop detailed designs\n"
            f"4. Deliver: {', '.join(deliverables)}"
        )

    async def _send_channel_message(self, channel_id: str, message: str):
        """Send a message to a channel.

        Args:
            channel_id: The channel to send to
            message: The message text
        """
        try:
            await self.messaging_adapter.send_channel_message(
                channel=channel_id,
                text=message,
            )
            logger.info(f"Sent message to channel {channel_id}")
        except Exception as e:
            logger.error(f"Failed to send channel message: {e}")

    @on_event("requirement_network.notification.agent_invited")
    async def handle_agent_invited(self, context: EventContext):
        """Handle invitation to a requirement channel.

        Args:
            context: The event context with invitation information
        """
        logger.info("=== RECEIVED AGENT INVITED EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        channel_id = data.get("channel_id")
        requirement_id = data.get("requirement_id")
        requirement_text = data.get("requirement_text", "")

        if not channel_id:
            logger.warning("Missing channel_id in invitation")
            return

        logger.info(f"Invited to channel: {channel_id}")
        logger.info(f"Requirement: {requirement_text[:100]}...")

        # Register capabilities (ensure they're up to date)
        await self._register_capabilities()

        # Join the channel
        logger.info(f"Joining requirement channel: {channel_id}")
        result = await self.requirement_adapter.join_requirement_channel(channel_id)

        if result.get("success"):
            self.joined_channels.add(channel_id)
            logger.info(f"Successfully joined channel {channel_id}")

            # Send introduction message
            await self._send_channel_message(
                channel_id,
                f"Designer here! I specialize in {', '.join(self.SKILLS[:3])}. "
                f"Ready to help with the design aspects of this requirement."
            )
        else:
            logger.error(f"Failed to join channel: {result.get('error')}")

    @on_event("requirement_network.notification.task_distributed")
    async def handle_task_distributed(self, context: EventContext):
        """Handle a task assignment from the coordinator.

        Args:
            context: The event context with task information
        """
        logger.info("=== RECEIVED TASK DISTRIBUTED EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        channel_id = data.get("channel_id")
        task_id = data.get("task_id")
        task = data.get("task", {})

        task_description = task.get("description", "")
        task_type = task.get("type", "")
        deliverables = task.get("deliverables", [])

        if not channel_id or not task_id:
            logger.warning("Missing channel_id or task_id in task distribution")
            return

        logger.info(f"Received task {task_id} in channel {channel_id}")
        logger.info(f"Task type: {task_type}")
        logger.info(f"Description: {task_description[:100]}...")
        logger.info(f"Expected deliverables: {deliverables}")

        # Analyze the task
        analysis = self._analyze_task(task_description, task_type)
        response_type = analysis["response_type"]

        logger.info(f"Task analysis result: {response_type}")

        # Respond to the task
        if response_type == "accept":
            result = await self.requirement_adapter.respond_to_task(
                channel_id=channel_id,
                task_id=task_id,
                response_type="accept",
                message=analysis["message"],
            )
        elif response_type == "reject":
            result = await self.requirement_adapter.respond_to_task(
                channel_id=channel_id,
                task_id=task_id,
                response_type="reject",
                reason=analysis["reason"],
            )
        else:  # propose
            result = await self.requirement_adapter.respond_to_task(
                channel_id=channel_id,
                task_id=task_id,
                response_type="propose",
                alternative=analysis["alternative"],
                message=analysis.get("message", ""),
            )

        if result.get("success"):
            logger.info(f"Successfully responded to task {task_id}: {response_type}")
        else:
            logger.error(f"Failed to respond to task: {result.get('error')}")


async def main():
    """Run the designer agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    designer = DesignerAgent(agent_id="designer")

    try:
        # Connect with workers group password
        await designer.async_start(
            network_host="localhost",
            network_port=8800,
            password_hash="3588bb7219b1faa3d01f132a0c60a394258ccc3049d8e4a243b737e62524d147",  # workers
        )
        print("Designer Agent running")
        print(f"Skills: {DesignerAgent.SKILLS}")
        print(f"Specialties: {DesignerAgent.SPECIALTIES}")
        print("Monitoring for agent_invited and task_distributed events")

        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await designer.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
