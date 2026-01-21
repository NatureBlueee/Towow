"""User Agent - represents user interactions."""

from typing import Any

from openagents.agents.base import BaseAgent


class UserAgent(BaseAgent):
    """Agent representing a user in the system."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        user_id: str,
    ):
        """Initialize the user agent.

        Args:
            agent_id: Unique identifier for the agent.
            name: Human-readable name for the agent.
            user_id: The user this agent represents.
        """
        super().__init__(agent_id, name)
        self.user_id = user_id

    async def process_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Process user-related messages.

        Args:
            message: The message to process.

        Returns:
            The response message.
        """
        # TODO: Implement user agent logic
        return {"status": "processed", "agent": self.agent_id, "user_id": self.user_id}

    async def start(self) -> None:
        """Start the user agent."""
        pass

    async def stop(self) -> None:
        """Stop the user agent."""
        pass
