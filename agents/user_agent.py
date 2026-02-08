#!/usr/bin/env python3
"""
User Agent for Requirement Demo Network.

This Python-based agent represents a user who:
1. Submits requirements in natural language
2. Monitors progress of submitted requirements
3. Receives updates when agents accept, reject, or propose alternatives
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


class UserAgent(WorkerAgent):
    """
    User agent that submits requirements and tracks progress.

    Capabilities:
    - Submit new requirements in natural language
    - Monitor progress of requirements
    - Receive updates when agents respond

    Workflow:
    1. Submit requirement using submit_requirement tool
    2. Receive channel_created confirmation
    3. Receive updates as agents accept/reject/propose
    """

    default_agent_id = "user"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize adapters
        self.requirement_adapter = RequirementNetworkAdapter()
        self.messaging_adapter = ThreadMessagingAgentAdapter()

        # Track submitted requirements: requirement_id -> {channel_id, text, status}
        self.submitted_requirements: Dict[str, Dict[str, Any]] = {}

        # Track task responses per requirement
        self.task_responses: Dict[str, List[Dict[str, Any]]] = {}

    async def on_startup(self):
        """Called after successful connection and setup."""
        # Bind adapters after client is initialized
        self.requirement_adapter.bind_client(self.client)
        self.requirement_adapter.bind_connector(self.client.connector)
        self.requirement_adapter.bind_agent(self.agent_id)

        self.messaging_adapter.bind_client(self.client)
        self.messaging_adapter.bind_connector(self.client.connector)
        self.messaging_adapter.bind_agent(self.agent_id)

        logger.info(f"User Agent '{self.client.agent_id}' started")
        logger.info("Ready to submit requirements and receive updates")

    async def submit_requirement(
        self,
        requirement_text: str,
        priority: str = "medium",
        deadline: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Submit a new requirement to the network.

        Args:
            requirement_text: Natural language description of the requirement
            priority: Priority level (low/medium/high)
            deadline: Optional deadline string
            tags: Optional list of tags

        Returns:
            Dict with submission result
        """
        logger.info(f"Submitting requirement: {requirement_text[:100]}...")
        logger.info(f"Priority: {priority}, Deadline: {deadline}, Tags: {tags}")

        result = await self.requirement_adapter.submit_requirement(
            requirement_text=requirement_text,
            priority=priority,
            deadline=deadline,
            tags=tags or [],
        )

        if result.get("success"):
            requirement_id = result.get("requirement_id")
            channel_id = result.get("channel_id")

            self.submitted_requirements[requirement_id] = {
                "channel_id": channel_id,
                "text": requirement_text,
                "priority": priority,
                "status": "submitted",
            }

            logger.info(f"Requirement submitted successfully!")
            logger.info(f"  - Requirement ID: {requirement_id}")
            logger.info(f"  - Channel ID: {channel_id}")

            # Initialize task responses tracker
            self.task_responses[requirement_id] = []
        else:
            logger.error(f"Failed to submit requirement: {result.get('error')}")

        return result

    def _format_update_message(self, update_type: str, data: Dict[str, Any]) -> str:
        """Format an update for display.

        Args:
            update_type: The type of update
            data: The update data

        Returns:
            Formatted message string
        """
        agent_id = data.get("agent_id", "unknown")
        task_id = data.get("task_id", "")

        if update_type == "task_accepted":
            message = data.get("content", {}).get("message", "Task accepted")
            return f"[ACCEPTED] Agent '{agent_id}' accepted the task.\nMessage: {message}"

        elif update_type == "task_rejected":
            reason = data.get("content", {}).get("reason", "No reason provided")
            return f"[REJECTED] Agent '{agent_id}' rejected the task.\nReason: {reason}"

        elif update_type == "task_proposed":
            alternative = data.get("content", {}).get("alternative", "Alternative proposal")
            msg = data.get("content", {}).get("message", "")
            text = f"[PROPOSAL] Agent '{agent_id}' proposed an alternative.\nProposal: {alternative}"
            if msg:
                text += f"\nNote: {msg}"
            return text

        else:
            return f"[UPDATE] {update_type}: {data}"

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

    @on_event("requirement_network.notification.user_update")
    async def handle_user_update(self, context: EventContext):
        """Handle updates about submitted requirements.

        Args:
            context: The event context with update information
        """
        logger.info("=== RECEIVED USER UPDATE EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        update_type = data.get("update_type")
        requirement_id = data.get("requirement_id")
        channel_id = data.get("channel_id")

        logger.info(f"Update type: {update_type}")
        logger.info(f"Requirement ID: {requirement_id}")

        # Format and display the update
        formatted = self._format_update_message(update_type, data)
        print(f"\n{'='*60}")
        print(f"UPDATE FOR REQUIREMENT: {requirement_id}")
        print(f"{'='*60}")
        print(formatted)
        print(f"{'='*60}\n")

        # Track the response
        if requirement_id:
            if requirement_id not in self.task_responses:
                self.task_responses[requirement_id] = []

            self.task_responses[requirement_id].append({
                "update_type": update_type,
                "agent_id": data.get("agent_id"),
                "content": data.get("content", {}),
            })

            # Update requirement status
            if requirement_id in self.submitted_requirements:
                accepted = sum(1 for r in self.task_responses[requirement_id] if r["update_type"] == "task_accepted")
                rejected = sum(1 for r in self.task_responses[requirement_id] if r["update_type"] == "task_rejected")
                proposed = sum(1 for r in self.task_responses[requirement_id] if r["update_type"] == "task_proposed")

                if accepted > 0:
                    self.submitted_requirements[requirement_id]["status"] = "in_progress"
                elif rejected > 0 and accepted == 0 and proposed == 0:
                    self.submitted_requirements[requirement_id]["status"] = "needs_attention"

        # Optionally send acknowledgment to channel
        if channel_id:
            if update_type == "task_accepted":
                await self._send_channel_message(
                    channel_id,
                    f"Thanks for accepting the task! Looking forward to your work."
                )
            elif update_type == "task_rejected":
                await self._send_channel_message(
                    channel_id,
                    f"I understand. Is there another agent who could help with this?"
                )
            elif update_type == "task_proposed":
                await self._send_channel_message(
                    channel_id,
                    f"Interesting proposal! Let me review the alternative approach."
                )

    def get_requirement_status(self, requirement_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a submitted requirement.

        Args:
            requirement_id: The requirement ID

        Returns:
            Status information or None if not found
        """
        if requirement_id not in self.submitted_requirements:
            return None

        req = self.submitted_requirements[requirement_id]
        responses = self.task_responses.get(requirement_id, [])

        return {
            "requirement_id": requirement_id,
            "channel_id": req["channel_id"],
            "text": req["text"],
            "priority": req["priority"],
            "status": req["status"],
            "responses": responses,
            "accepted_count": sum(1 for r in responses if r["update_type"] == "task_accepted"),
            "rejected_count": sum(1 for r in responses if r["update_type"] == "task_rejected"),
            "proposed_count": sum(1 for r in responses if r["update_type"] == "task_proposed"),
        }

    def list_requirements(self) -> List[Dict[str, Any]]:
        """List all submitted requirements and their status.

        Returns:
            List of requirement status dicts
        """
        return [
            self.get_requirement_status(req_id)
            for req_id in self.submitted_requirements
        ]


async def main():
    """Run the user agent with an interactive demo."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    user = UserAgent(agent_id="user")

    try:
        # Connect with users group password
        await user.async_start(
            network_host="localhost",
            network_port=8800,
            password_hash="04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb",  # users
        )
        print("User Agent running")
        print("Ready to submit requirements and receive updates")
        print("\n" + "="*60)
        print("INTERACTIVE MODE")
        print("="*60)
        print("Commands:")
        print("  submit <text>  - Submit a new requirement")
        print("  status         - Show all requirements and their status")
        print("  quit           - Exit the agent")
        print("="*60 + "\n")

        # Interactive loop
        while True:
            try:
                # Use asyncio for non-blocking input
                loop = asyncio.get_event_loop()
                user_input = await loop.run_in_executor(None, input, "user> ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() == "quit":
                    break

                elif user_input.lower() == "status":
                    requirements = user.list_requirements()
                    if not requirements:
                        print("No requirements submitted yet.")
                    else:
                        print("\n" + "="*60)
                        print("SUBMITTED REQUIREMENTS")
                        print("="*60)
                        for req in requirements:
                            print(f"\nRequirement: {req['requirement_id']}")
                            print(f"  Text: {req['text'][:50]}...")
                            print(f"  Status: {req['status']}")
                            print(f"  Channel: {req['channel_id']}")
                            print(f"  Responses: {req['accepted_count']} accepted, "
                                  f"{req['rejected_count']} rejected, "
                                  f"{req['proposed_count']} proposed")
                        print("="*60 + "\n")

                elif user_input.lower().startswith("submit "):
                    requirement_text = user_input[7:].strip()
                    if requirement_text:
                        result = await user.submit_requirement(requirement_text)
                        if result.get("success"):
                            print(f"\nRequirement submitted!")
                            print(f"  ID: {result.get('requirement_id')}")
                            print(f"  Channel: {result.get('channel_id')}")
                            print("Waiting for agent responses...\n")
                    else:
                        print("Please provide a requirement description.")

                else:
                    print("Unknown command. Use 'submit <text>', 'status', or 'quit'")

            except EOFError:
                break

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await user.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
