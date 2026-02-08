"""
Bridge Agent - 连接 Web 服务和 OpenAgents 网络

功能：
1. 连接到 OpenAgents 网络
2. 提供 submit_requirement() 方法，触发 channel_created 事件
3. 监听 OpenAgents 网络消息，转发到 WebSocketManager
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add local mods folder to path for requirement_network adapter
_script_dir = Path(__file__).parent.parent
_mods_dir = _script_dir / "mods"
if _mods_dir.exists() and str(_mods_dir) not in sys.path:
    sys.path.insert(0, str(_mods_dir))

from openagents.agents.worker_agent import WorkerAgent, on_event
from openagents.models.event_context import EventContext
from requirement_network import RequirementNetworkAdapter

from .websocket_manager import get_websocket_manager

logger = logging.getLogger(__name__)


class BridgeAgent(WorkerAgent):
    """
    Bridge Agent - 连接 Web 服务和 OpenAgents 网络

    职责：
    1. 作为 Web 服务的代理，向 OpenAgents 网络提交需求
    2. 监听网络事件，转发到 WebSocket 客户端
    """

    default_agent_id = "bridge"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.requirement_adapter = RequirementNetworkAdapter()
        self._connected = False

    async def on_startup(self):
        """Called after successful connection and setup."""
        self.requirement_adapter.bind_client(self.client)
        self.requirement_adapter.bind_connector(self.client.connector)
        self.requirement_adapter.bind_agent(self.agent_id)
        self._connected = True
        logger.info(f"BridgeAgent '{self.client.agent_id}' connected to OpenAgents network")

    @property
    def is_connected(self) -> bool:
        """Check if the agent is connected to the network."""
        return self._connected

    async def submit_requirement(
        self,
        requirement_id: str,
        requirement_text: str,
        channel_id: str,
        submitter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit a requirement to the OpenAgents network.

        This triggers the channel_created event which will be handled by AdminAgent.

        Args:
            requirement_id: Unique ID for the requirement
            requirement_text: The requirement description
            channel_id: The channel ID for this requirement
            submitter_id: Optional submitter agent ID

        Returns:
            Dict with success status and channel info
        """
        if not self._connected:
            logger.error("BridgeAgent not connected to network")
            return {"success": False, "error": "not_connected"}

        try:
            # Submit requirement through the adapter
            result = await self.requirement_adapter.submit_requirement(
                requirement_text=requirement_text,
                tags=[requirement_id],  # Use tags to pass requirement_id
            )

            if result.get("success"):
                logger.info(f"Requirement submitted: {requirement_id}, channel: {result.get('channel_id')}")
                return {
                    "success": True,
                    "requirement_id": requirement_id,
                    "channel_id": result.get("channel_id", channel_id),
                }
            else:
                logger.error(f"Failed to submit requirement: {result.get('error')}")
                return {"success": False, "error": result.get("error")}

        except Exception as e:
            logger.error(f"Error submitting requirement: {e}")
            return {"success": False, "error": str(e)}

    # ============ Event Handlers - Forward to WebSocket ============

    @on_event("requirement_network.notification.agent_invited")
    async def handle_agent_invited(self, context: EventContext):
        """Handle agent invited notification - forward to WebSocket."""
        logger.info("=== RECEIVED AGENT INVITED EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        await self._forward_to_websocket("agent_invited", data)

    @on_event("requirement_network.notification.task_distributed")
    async def handle_task_distributed(self, context: EventContext):
        """Handle task distributed notification - forward to WebSocket."""
        logger.info("=== RECEIVED TASK DISTRIBUTED EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        await self._forward_to_websocket("task_distributed", data)

    @on_event("requirement_network.notification.task_response")
    async def handle_task_response(self, context: EventContext):
        """Handle task response notification - forward to WebSocket."""
        logger.info("=== RECEIVED TASK RESPONSE EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        await self._forward_to_websocket("task_response", data)

    @on_event("messaging.channel_message")
    async def handle_channel_message(self, context: EventContext):
        """Handle channel message - forward to WebSocket."""
        logger.info("=== RECEIVED CHANNEL MESSAGE EVENT ===")
        data = context.incoming_event.payload
        logger.info(f"Payload: {data}")

        await self._forward_to_websocket("channel_message", data)

    async def _forward_to_websocket(self, event_type: str, data: Dict[str, Any]):
        """Forward an event to WebSocket clients."""
        try:
            ws_manager = get_websocket_manager()
            channel_id = data.get("channel_id")

            message = {
                "type": event_type,
                "payload": data,
            }

            if channel_id:
                # Broadcast to channel subscribers
                count = await ws_manager.broadcast_to_channel(channel_id, message)
                logger.info(f"Forwarded {event_type} to {count} subscribers in channel {channel_id}")
            else:
                # Broadcast to all connected clients
                count = await ws_manager.broadcast_all(message)
                logger.info(f"Forwarded {event_type} to {count} clients")

        except Exception as e:
            logger.error(f"Error forwarding event to WebSocket: {e}")


# ============ Singleton Instance ============

_bridge_agent: Optional[BridgeAgent] = None
_bridge_task: Optional[asyncio.Task] = None
_bridge_lock = asyncio.Lock()


async def get_bridge_agent() -> Optional[BridgeAgent]:
    """Get the singleton BridgeAgent instance."""
    global _bridge_agent
    return _bridge_agent


async def start_bridge_agent(
    network_host: str = "localhost",
    network_port: int = 8800,
) -> BridgeAgent:
    """
    Start the BridgeAgent and connect to the OpenAgents network.

    Args:
        network_host: OpenAgents network host
        network_port: OpenAgents network port

    Returns:
        The started BridgeAgent instance
    """
    global _bridge_agent, _bridge_task

    async with _bridge_lock:
        if _bridge_agent is not None and _bridge_agent.is_connected:
            logger.info("BridgeAgent already running")
            return _bridge_agent

        _bridge_agent = BridgeAgent(agent_id="bridge")

        # Bridge uses workers group password
        # Read from environment variable, fallback to default for development
        default_hash = "3588bb7219b1faa3d01f132a0c60a394258ccc3049d8e4a243b737e62524d147"
        workers_password_hash = os.environ.get("OPENAGENTS_WORKERS_PASSWORD_HASH", default_hash)
        if workers_password_hash == default_hash:
            logger.warning(
                "Using default workers password hash. "
                "Set OPENAGENTS_WORKERS_PASSWORD_HASH environment variable for production."
            )

        async def run_agent():
            try:
                await _bridge_agent.async_start(
                    network_host=network_host,
                    network_port=network_port,
                    password_hash=workers_password_hash,
                )
                logger.info("BridgeAgent started successfully")

                # Keep running
                while _bridge_agent is not None:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"BridgeAgent error: {e}")
            finally:
                if _bridge_agent:
                    await _bridge_agent.async_stop()

        _bridge_task = asyncio.create_task(run_agent())

        # Wait for connection
        for _ in range(50):  # Wait up to 5 seconds
            await asyncio.sleep(0.1)
            if _bridge_agent.is_connected:
                break

        if not _bridge_agent.is_connected:
            logger.warning("BridgeAgent connection timeout, may still be connecting...")

        return _bridge_agent


async def stop_bridge_agent():
    """Stop the BridgeAgent."""
    global _bridge_agent, _bridge_task

    async with _bridge_lock:
        if _bridge_agent is None:
            return

        logger.info("Stopping BridgeAgent...")

        agent = _bridge_agent
        _bridge_agent = None

        if _bridge_task:
            _bridge_task.cancel()
            try:
                await _bridge_task
            except asyncio.CancelledError:
                pass
            _bridge_task = None

        try:
            await agent.async_stop()
        except Exception as e:
            logger.error(f"Error stopping BridgeAgent: {e}")

        logger.info("BridgeAgent stopped")
