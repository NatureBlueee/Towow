#!/usr/bin/env python3
"""
Admin Agent for Requirement Demo Network.

This Python-based agent monitors for channel_created events and:
1. Reads the agent registry to find relevant agents
2. Analyzes the requirement to select appropriate agents
3. Invites selected agents to the requirement channel
4. Signals when invitations are complete
"""

import asyncio
import logging
import re
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

logger = logging.getLogger(__name__)


class AdminAgent(WorkerAgent):
    """
    Admin agent that manages agent invitations for requirement channels.

    Workflow:
    1. Receive requirement_network.channel_created event
    2. Read agent registry to find all available agents
    3. Analyze requirement to determine relevant skills
    4. Invite agents with matching capabilities
    5. Signal that invitations are complete
    """

    default_agent_id = "admin"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize the requirement network adapter
        self.requirement_adapter = RequirementNetworkAdapter()

        # Keyword to skills mapping for simple matching
        self.skill_keywords = {
            "design": ["design", "ui", "ux", "figma", "mockup", "visual", "layout", "interface"],
            "development": ["develop", "code", "programming", "implement", "build", "software", "app"],
            "frontend": ["frontend", "react", "vue", "angular", "html", "css", "javascript", "web"],
            "backend": ["backend", "api", "server", "database", "python", "node", "java"],
            "analysis": ["analyze", "research", "data", "report", "study", "investigate"],
            "testing": ["test", "qa", "quality", "bug", "verify", "validate"],
        }

    async def on_startup(self):
        """Called after successful connection and setup."""
        # Bind the adapter after client is initialized
        self.requirement_adapter.bind_client(self.client)
        self.requirement_adapter.bind_connector(self.client.connector)
        self.requirement_adapter.bind_agent(self.agent_id)

        logger.info(f"Admin Agent '{self.client.agent_id}' started")
        logger.info("Monitoring for requirement_network.channel_created events")

    def _extract_skills_from_requirement(self, requirement_text: str) -> List[str]:
        """Extract relevant skills from the requirement text.

        Uses simple keyword matching to determine which skills are needed.

        Args:
            requirement_text: The requirement description

        Returns:
            List of skill categories that match the requirement
        """
        requirement_lower = requirement_text.lower()
        matched_skills = []

        for skill, keywords in self.skill_keywords.items():
            for keyword in keywords:
                if keyword in requirement_lower:
                    if skill not in matched_skills:
                        matched_skills.append(skill)
                    break

        # If no skills matched, default to development and design
        if not matched_skills:
            logger.info("No specific skills matched, using defaults: design, development")
            matched_skills = ["design", "development"]

        return matched_skills

    def _select_agents_for_requirement(
        self,
        requirement_text: str,
        registry_agents: List[Dict[str, Any]],
    ) -> List[str]:
        """Select relevant agents based on requirement analysis.

        Args:
            requirement_text: The requirement description
            registry_agents: List of registered agents from the registry

        Returns:
            List of agent IDs to invite
        """
        # Extract needed skills from requirement
        needed_skills = self._extract_skills_from_requirement(requirement_text)
        logger.info(f"Extracted needed skills: {needed_skills}")

        selected_agents = []

        for agent in registry_agents:
            agent_id = agent.get("agent_id", "")
            capabilities = agent.get("capabilities", {})
            agent_skills = capabilities.get("skills", [])
            agent_specialties = capabilities.get("specialties", [])

            # Skip admin and coordinator agents
            if agent_id in ["admin", "coordinator"]:
                continue

            # Check if agent has any of the needed skills
            all_agent_capabilities = [s.lower() for s in agent_skills + agent_specialties]

            for needed_skill in needed_skills:
                # Check for direct match or partial match
                for cap in all_agent_capabilities:
                    if needed_skill in cap or cap in needed_skill:
                        if agent_id not in selected_agents:
                            selected_agents.append(agent_id)
                            logger.info(f"Selected agent {agent_id} for skill: {needed_skill}")
                        break

        # If no agents matched, select all worker agents
        if not selected_agents:
            logger.info("No specific matches, selecting all worker agents")
            for agent in registry_agents:
                agent_id = agent.get("agent_id", "")
                agent_group = agent.get("agent_group", "")
                if agent_group == "workers" or agent_id not in ["admin", "coordinator"]:
                    if agent_id not in selected_agents:
                        selected_agents.append(agent_id)

        return selected_agents

    @on_event("requirement_network.channel_created")
    async def handle_channel_created(self, context: EventContext):
        """Handle new requirement channel - read registry and invite agents.

        Args:
            context: The event context with channel information
        """
        logger.info("=== RECEIVED CHANNEL CREATED EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        channel_id = data.get("channel_id")
        requirement_id = data.get("requirement_id")
        requirement_text = data.get("requirement_text", "")
        creator_id = data.get("creator_id")

        if not channel_id or not requirement_text:
            logger.warning(f"Missing channel_id or requirement_text: {data}")
            return

        logger.info(f"New requirement channel: {channel_id}")
        logger.info(f"Requirement: {requirement_text[:100]}...")
        logger.info(f"Creator: {creator_id}")

        # Step 1: Read the agent registry
        logger.info("Reading agent registry...")
        registry_result = await self.requirement_adapter.read_agent_registry()

        if not registry_result.get("success"):
            logger.error(f"Failed to read registry: {registry_result.get('error')}")
            return

        registry_agents = registry_result.get("agents", [])
        logger.info(f"Found {len(registry_agents)} agents in registry")

        for agent in registry_agents:
            logger.info(f"  - {agent.get('agent_id')}: {agent.get('capabilities', {}).get('skills', [])}")

        # Step 2: Select relevant agents based on requirement
        selected_agents = self._select_agents_for_requirement(requirement_text, registry_agents)
        logger.info(f"Selected agents to invite: {selected_agents}")

        if not selected_agents:
            logger.warning("No agents to invite for this requirement")
            # Still signal completion
            await self.requirement_adapter.signal_invitations_complete(channel_id)
            return

        # Step 3: Invite selected agents
        logger.info(f"Inviting {len(selected_agents)} agents to channel {channel_id}")
        invite_result = await self.requirement_adapter.invite_agents(
            channel_id=channel_id,
            agent_ids=selected_agents,
        )

        if invite_result.get("success"):
            logger.info(f"Successfully invited agents: {selected_agents}")
        else:
            logger.error(f"Failed to invite agents: {invite_result.get('error')}")

        # Step 4: Signal invitations complete
        # Give agents a moment to receive invitations, then signal completion
        await asyncio.sleep(1.0)

        logger.info(f"Signaling invitations complete for {channel_id}")
        complete_result = await self.requirement_adapter.signal_invitations_complete(channel_id)

        if complete_result.get("success"):
            logger.info(f"Invitations complete signal sent for {channel_id}")
        else:
            logger.error(f"Failed to signal completion: {complete_result.get('error')}")


async def main():
    """Run the admin agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    admin = AdminAgent(agent_id="admin")

    try:
        # Connect with admin group password
        await admin.async_start(
            network_host="localhost",
            network_port=8800,
            password_hash="8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # admin
        )
        print("Admin Agent running")
        print("Monitoring for requirement_network.channel_created events")
        print("Will read registry and invite relevant agents")

        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await admin.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
