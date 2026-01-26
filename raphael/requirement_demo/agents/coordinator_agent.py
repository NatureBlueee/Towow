#!/usr/bin/env python3
"""
Coordinator Agent for Requirement Demo Network.

This Python-based agent listens for invitations_complete events and:
1. Reads the requirement details
2. Analyzes the invited agents' capabilities
3. Creates and distributes tasks to each agent
4. Handles agent responses (accept/reject/propose)
5. Notifies the user of progress
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

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


class CoordinatorAgent(WorkerAgent):
    """
    Coordinator agent that distributes tasks and manages responses.

    Workflow:
    1. Receive requirement_network.invitations_complete event
    2. Read requirement details and invited agents
    3. Create task distribution plan
    4. Distribute tasks to each agent
    5. Track responses and handle accept/reject/propose
    6. Notify user of progress
    """

    default_agent_id = "coordinator"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize adapters
        self.requirement_adapter = RequirementNetworkAdapter()
        self.messaging_adapter = ThreadMessagingAgentAdapter()

        # Track pending tasks per channel: channel_id -> {agent_id: task_status}
        self.pending_tasks: Dict[str, Dict[str, str]] = {}

        # Track task details: task_id -> {channel_id, agent_id, task}
        self.task_details: Dict[str, Dict[str, Any]] = {}

    async def on_startup(self):
        """Called after successful connection and setup."""
        # Bind the adapters after client is initialized
        self.requirement_adapter.bind_client(self.client)
        self.requirement_adapter.bind_connector(self.client.connector)
        self.requirement_adapter.bind_agent(self.agent_id)

        self.messaging_adapter.bind_client(self.client)
        self.messaging_adapter.bind_connector(self.client.connector)
        self.messaging_adapter.bind_agent(self.agent_id)

        logger.info(f"Coordinator Agent '{self.client.agent_id}' started")
        logger.info("Monitoring for invitations_complete and task_response events")

    def _create_task_plan(
        self,
        requirement_text: str,
        invited_agents: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Create a task distribution plan based on requirement and agents.

        Args:
            requirement_text: The requirement description
            invited_agents: List of invited agent IDs

        Returns:
            Dict mapping agent_id to task details
        """
        task_plan = {}
        requirement_lower = requirement_text.lower()

        for agent_id in invited_agents:
            # Create task based on agent role (simple heuristic)
            if "designer" in agent_id.lower():
                task = {
                    "description": f"Design the visual aspects for: {requirement_text}",
                    "type": "design",
                    "deliverables": ["mockups", "wireframes", "style guide"],
                }
            elif "developer" in agent_id.lower():
                task = {
                    "description": f"Implement the technical solution for: {requirement_text}",
                    "type": "development",
                    "deliverables": ["code", "tests", "documentation"],
                }
            elif "analyst" in agent_id.lower():
                task = {
                    "description": f"Analyze and research: {requirement_text}",
                    "type": "analysis",
                    "deliverables": ["report", "recommendations"],
                }
            else:
                # Generic task
                task = {
                    "description": f"Contribute to: {requirement_text}",
                    "type": "general",
                    "deliverables": ["output"],
                }

            task_plan[agent_id] = task

        return task_plan

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

    @on_event("requirement_network.invitations_complete")
    async def handle_invitations_complete(self, context: EventContext):
        """Handle invitations complete - distribute tasks to agents.

        Args:
            context: The event context with channel and agent information
        """
        logger.info("=== RECEIVED INVITATIONS COMPLETE EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        channel_id = data.get("channel_id")
        requirement_id = data.get("requirement_id")
        requirement_text = data.get("requirement_text", "")
        invited_agents = data.get("invited_agents", [])

        if not channel_id or not invited_agents:
            logger.warning(f"Missing channel_id or invited_agents: {data}")
            return

        logger.info(f"Invitations complete for channel: {channel_id}")
        logger.info(f"Requirement: {requirement_text[:100]}...")
        logger.info(f"Invited agents: {invited_agents}")

        # Initialize pending tasks for this channel
        self.pending_tasks[channel_id] = {agent_id: "pending" for agent_id in invited_agents}

        # Send announcement to channel
        await self._send_channel_message(
            channel_id,
            f"Coordinator here. All agents have been invited. "
            f"Requirement: {requirement_text}\n\n"
            f"I will now distribute tasks to each agent."
        )

        # Create task distribution plan
        task_plan = self._create_task_plan(requirement_text, invited_agents)

        # Distribute tasks to each agent
        for agent_id, task in task_plan.items():
            logger.info(f"Distributing task to {agent_id}: {task['description'][:50]}...")

            result = await self.requirement_adapter.distribute_task(
                channel_id=channel_id,
                agent_id=agent_id,
                task_description=task["description"],
                task_details={
                    "type": task["type"],
                    "deliverables": task["deliverables"],
                },
            )

            if result.get("success"):
                task_id = result.get("task_id")
                self.task_details[task_id] = {
                    "channel_id": channel_id,
                    "agent_id": agent_id,
                    "task": task,
                }
                logger.info(f"Task {task_id} distributed to {agent_id}")

                # Send notification to channel
                await self._send_channel_message(
                    channel_id,
                    f"Task assigned to @{agent_id}:\n"
                    f"- Type: {task['type']}\n"
                    f"- Description: {task['description']}\n"
                    f"- Deliverables: {', '.join(task['deliverables'])}"
                )
            else:
                logger.error(f"Failed to distribute task to {agent_id}: {result.get('error')}")

        logger.info(f"Task distribution complete for channel {channel_id}")

    @on_event("requirement_network.notification.task_response")
    async def handle_task_response(self, context: EventContext):
        """Handle agent response to a task.

        Args:
            context: The event context with response information
        """
        logger.info("=== RECEIVED TASK RESPONSE EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        channel_id = data.get("channel_id")
        task_id = data.get("task_id")
        agent_id = data.get("agent_id")
        response_type = data.get("response_type")
        content = data.get("content", {})

        logger.info(f"Task {task_id} response from {agent_id}: {response_type}")

        # Update tracking
        if channel_id in self.pending_tasks:
            self.pending_tasks[channel_id][agent_id] = response_type

        if response_type == "accept":
            await self._handle_accept(channel_id, task_id, agent_id, content)
        elif response_type == "reject":
            await self._handle_reject(channel_id, task_id, agent_id, content)
        elif response_type == "propose":
            await self._handle_proposal(channel_id, task_id, agent_id, content)

        # Check if all tasks are resolved
        await self._check_completion(channel_id)

    async def _handle_accept(
        self,
        channel_id: str,
        task_id: str,
        agent_id: str,
        content: Dict[str, Any],
    ):
        """Handle task acceptance.

        Args:
            channel_id: The channel ID
            task_id: The task ID
            agent_id: The agent who accepted
            content: Response content
        """
        message = content.get("message", "Task accepted")

        await self._send_channel_message(
            channel_id,
            f"@{agent_id} has ACCEPTED the task.\n"
            f"Message: {message}\n"
            f"Work will begin shortly."
        )

        logger.info(f"Agent {agent_id} accepted task {task_id}")

    async def _handle_reject(
        self,
        channel_id: str,
        task_id: str,
        agent_id: str,
        content: Dict[str, Any],
    ):
        """Handle task rejection.

        Args:
            channel_id: The channel ID
            task_id: The task ID
            agent_id: The agent who rejected
            content: Response content with reason
        """
        reason = content.get("reason", "No reason provided")

        await self._send_channel_message(
            channel_id,
            f"@{agent_id} has REJECTED the task.\n"
            f"Reason: {reason}\n"
            f"We may need to find an alternative agent."
        )

        logger.info(f"Agent {agent_id} rejected task {task_id}: {reason}")

        # TODO: Could implement finding an alternative agent here

    async def _handle_proposal(
        self,
        channel_id: str,
        task_id: str,
        agent_id: str,
        content: Dict[str, Any],
    ):
        """Handle alternative proposal.

        Args:
            channel_id: The channel ID
            task_id: The task ID
            agent_id: The agent who proposed
            content: Response content with alternative
        """
        alternative = content.get("alternative", "Alternative proposal")
        message = content.get("message", "")

        await self._send_channel_message(
            channel_id,
            f"@{agent_id} has proposed an ALTERNATIVE approach.\n"
            f"Proposal: {alternative}\n"
            f"{f'Additional notes: {message}' if message else ''}\n"
            f"Please review and provide feedback."
        )

        logger.info(f"Agent {agent_id} proposed alternative for task {task_id}")

        # TODO: Could implement proposal negotiation here

    async def _check_completion(self, channel_id: str):
        """Check if all tasks in a channel are resolved.

        Args:
            channel_id: The channel to check
        """
        if channel_id not in self.pending_tasks:
            return

        tasks = self.pending_tasks[channel_id]
        all_resolved = all(status != "pending" for status in tasks.values())

        if all_resolved:
            # Summarize results
            accepted = [a for a, s in tasks.items() if s == "accept"]
            rejected = [a for a, s in tasks.items() if s == "reject"]
            proposed = [a for a, s in tasks.items() if s == "propose"]

            summary = f"All tasks have been responded to!\n\n"
            if accepted:
                summary += f"ACCEPTED by: {', '.join(accepted)}\n"
            if rejected:
                summary += f"REJECTED by: {', '.join(rejected)}\n"
            if proposed:
                summary += f"PROPOSALS from: {', '.join(proposed)}\n"

            await self._send_channel_message(channel_id, summary)

            logger.info(f"Channel {channel_id} task distribution complete: {tasks}")


async def main():
    """Run the coordinator agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    coordinator = CoordinatorAgent(agent_id="coordinator")

    try:
        # Connect with coordinator group password
        await coordinator.async_start(
            network_host="localhost",
            network_port=8800,
            password_hash="bf24385098410391a81d92b2de72d3a2946d24f42ee387e51004a868281a2408",  # coordinator
        )
        print("Coordinator Agent running")
        print("Monitoring for invitations_complete and task_response events")
        print("Will distribute tasks and handle responses")

        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await coordinator.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
