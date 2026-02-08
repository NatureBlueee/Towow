#!/usr/bin/env python3
"""
Developer Agent for Requirement Demo Network.

This Python-based agent handles software development tasks:
1. Registers development capabilities when invited to a channel
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


class DeveloperAgent(WorkerAgent):
    """
    Developer agent that handles software development tasks.

    Capabilities:
    - Full-stack web development
    - Python, JavaScript, TypeScript programming
    - React, Vue, and modern frontend frameworks
    - Backend APIs and databases
    - Testing and code quality

    Workflow:
    1. Receive agent_invited event -> register capabilities, join channel
    2. Receive task_distributed event -> analyze and respond (accept/reject/propose)
    """

    default_agent_id = "developer"

    # Define developer's capabilities
    SKILLS = ["python", "javascript", "typescript", "react", "nodejs", "sql", "git"]
    SPECIALTIES = ["web-development", "api-design", "frontend", "backend", "testing"]

    # Keywords that indicate development work
    DEV_KEYWORDS = [
        "code", "implement", "develop", "build", "programming", "api", "database",
        "backend", "frontend", "server", "function", "class", "module", "test",
        "debug", "deploy", "integrate", "endpoint", "react", "vue", "python",
        "javascript", "typescript", "sql", "git", "software", "app", "application"
    ]

    # Keywords that indicate non-development work (should reject)
    NON_DEV_KEYWORDS = [
        "design", "mockup", "wireframe", "visual", "color", "typography",
        "illustration", "branding", "logo", "figma", "photoshop", "sketch"
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

        logger.info(f"Developer Agent '{self.client.agent_id}' started")
        logger.info(f"Skills: {self.SKILLS}")
        logger.info(f"Specialties: {self.SPECIALTIES}")

        # Register capabilities on startup
        await self._register_capabilities()

    async def _register_capabilities(self):
        """Register the developer's capabilities with the network."""
        logger.info("Registering development capabilities...")

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

        # Check if it's clearly development-related
        dev_matches = sum(1 for kw in self.DEV_KEYWORDS if kw in description_lower)
        non_dev_matches = sum(1 for kw in self.NON_DEV_KEYWORDS if kw in description_lower)

        # Also check task type
        if type_lower in ["development", "coding", "backend", "frontend", "testing", "general"]:
            dev_matches += 3
        elif type_lower in ["design", "ui", "ux", "visual"]:
            non_dev_matches += 3

        logger.info(f"Task analysis - dev keywords: {dev_matches}, non-dev: {non_dev_matches}")

        if dev_matches > non_dev_matches:
            # Accept the task
            return {
                "response_type": "accept",
                "message": self._generate_acceptance_message(task_description),
            }
        elif non_dev_matches > dev_matches:
            # Reject - not a development task
            return {
                "response_type": "reject",
                "reason": "This task appears to be focused on visual design, "
                          "which is outside my development expertise. "
                          "A designer would be better suited for this work.",
            }
        else:
            # Propose an alternative - maybe we can help with technical aspects
            return {
                "response_type": "propose",
                "alternative": "I can help with the technical implementation aspects of this task, "
                              "including building the frontend components, backend logic, and APIs. "
                              "The visual design work would need a designer.",
                "message": "I notice this task has both technical and design components.",
            }

    def _generate_acceptance_message(self, task_description: str) -> str:
        """Generate an acceptance message with a brief technical plan.

        Args:
            task_description: The task description

        Returns:
            Acceptance message with plan
        """
        description_lower = task_description.lower()

        approach = []
        if any(kw in description_lower for kw in ["api", "backend", "server", "endpoint"]):
            approach.append("build RESTful API endpoints")
        if any(kw in description_lower for kw in ["frontend", "ui", "react", "vue", "component"]):
            approach.append("implement frontend components")
        if any(kw in description_lower for kw in ["database", "sql", "data", "store"]):
            approach.append("set up database schema and queries")
        if any(kw in description_lower for kw in ["test", "testing", "unit", "integration"]):
            approach.append("write comprehensive tests")
        if any(kw in description_lower for kw in ["deploy", "ci", "cd", "pipeline"]):
            approach.append("configure deployment pipeline")

        if not approach:
            approach = ["implement the core functionality", "write tests", "document the code"]

        return (
            f"I'll work on this development task. My technical plan:\n"
            f"1. Analyze requirements and architecture\n"
            f"2. Set up development environment\n"
            f"3. {approach[0].capitalize()}\n"
            f"4. {approach[1].capitalize() if len(approach) > 1 else 'Write tests'}\n"
            f"5. Code review and documentation"
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
                f"Developer here! I specialize in {', '.join(self.SKILLS[:4])}. "
                f"Ready to help with the technical implementation of this requirement."
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
    """Run the developer agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    developer = DeveloperAgent(agent_id="developer")

    try:
        # Connect with workers group password
        await developer.async_start(
            network_host="localhost",
            network_port=8800,
            password_hash="3588bb7219b1faa3d01f132a0c60a394258ccc3049d8e4a243b737e62524d147",  # workers
        )
        print("Developer Agent running")
        print(f"Skills: {DeveloperAgent.SKILLS}")
        print(f"Specialties: {DeveloperAgent.SPECIALTIES}")
        print("Monitoring for agent_invited and task_distributed events")

        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await developer.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
