#!/usr/bin/env python3
"""
Test script to submit a requirement and verify the multi-agent collaboration flow.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add local mods folder to path
_script_dir = Path(__file__).parent
_mods_dir = _script_dir / "mods"
if _mods_dir.exists() and str(_mods_dir) not in sys.path:
    sys.path.insert(0, str(_mods_dir))

from openagents.agents.worker_agent import WorkerAgent, on_event
from openagents.models.event_context import EventContext
from requirement_network import RequirementNetworkAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestRequester(WorkerAgent):
    """Simple test agent to submit a requirement."""

    default_agent_id = "test_requester"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.requirement_adapter = RequirementNetworkAdapter()
        self.updates_received = []

    async def on_startup(self):
        """Bind adapters after connection."""
        self.requirement_adapter.bind_client(self.client)
        self.requirement_adapter.bind_connector(self.client.connector)
        self.requirement_adapter.bind_agent(self.agent_id)
        logger.info(f"Test requester '{self.agent_id}' ready")

    @on_event("requirement_network.notification.user_update")
    async def handle_update(self, context: EventContext):
        """Handle updates about the requirement."""
        data = context.incoming_event.payload
        logger.info(f"Received update: {data}")
        self.updates_received.append(data)
        print(f"\n{'='*60}")
        print(f"UPDATE: {data.get('update_type')}")
        print(f"Agent: {data.get('agent_id')}")
        print(f"Content: {data.get('content')}")
        print(f"{'='*60}\n")


async def main():
    """Submit a test requirement."""
    agent = TestRequester(agent_id="test_requester")

    try:
        # Connect with users group password
        await agent.async_start(
            network_host="localhost",
            network_port=8800,
            password_hash="04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb",
        )

        print("\n" + "="*60)
        print("TEST: Submitting requirement...")
        print("="*60 + "\n")

        # Submit a test requirement
        result = await agent.requirement_adapter.submit_requirement(
            requirement_text="我需要一个 Web3 钱包集成方案，支持 MetaMask 和 WalletConnect，用于我们的 AI 产品",
            priority="high",
            tags=["Web3", "AI产品", "钱包集成"],
        )

        print(f"\nSubmission result: {result}")

        if result.get("success"):
            print(f"\nRequirement submitted successfully!")
            print(f"  Requirement ID: {result.get('requirement_id')}")
            print(f"  Channel ID: {result.get('channel_id')}")
            print("\nWaiting for agent responses (30 seconds)...")

            # Wait for responses
            await asyncio.sleep(30)

            print(f"\nReceived {len(agent.updates_received)} updates")
            for update in agent.updates_received:
                print(f"  - {update.get('update_type')} from {update.get('agent_id')}")
        else:
            print(f"\nFailed to submit: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await agent.async_stop()
        print("\nTest complete.")


if __name__ == "__main__":
    asyncio.run(main())
