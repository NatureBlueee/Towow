"""ToWow Base Agent class - 独立基类实现."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class EventContext:
    """Event context for agent messages."""

    def __init__(self, incoming_event: Any = None):
        """Initialize event context.

        Args:
            incoming_event: The incoming event data.
        """
        self.incoming_event = incoming_event or _MockEvent()


class ChannelMessageContext(EventContext):
    """Context for channel messages."""

    def __init__(self, channel: str = "", message: Optional[Dict[str, Any]] = None, **kwargs: Any):
        """Initialize channel message context.

        Args:
            channel: The channel name.
            message: The message data.
            **kwargs: Additional arguments.
        """
        super().__init__(**kwargs)
        self.channel = channel
        self.message = message or {}


class _MockEvent:
    """Mock event for when no real event is provided."""

    def __init__(self):
        self.payload = {"content": {}}


class _MockWorkspace:
    """Mock workspace for agent operations."""

    def __init__(self, agent: "TowowBaseAgent"):
        self._agent = agent

    def agent(self, agent_id: str) -> "_MockAgentHandle":
        """Get a handle to another agent.

        Args:
            agent_id: The target agent ID.

        Returns:
            Agent handle for sending messages.
        """
        return _MockAgentHandle(agent_id, self._agent)

    def channel(self, channel_name: str) -> "_MockChannelHandle":
        """Get a handle to a channel.

        Args:
            channel_name: The channel name.

        Returns:
            Channel handle for posting messages.
        """
        return _MockChannelHandle(channel_name, self._agent)

    async def list_agents(self) -> List[str]:
        """List online agents.

        Returns:
            List of agent IDs.
        """
        return []

    async def channels(self) -> List[str]:
        """List available channels.

        Returns:
            List of channel names.
        """
        return []


class _MockAgentHandle:
    """Handle for sending messages to an agent."""

    def __init__(self, agent_id: str, source_agent: "TowowBaseAgent"):
        self._agent_id = agent_id
        self._source = source_agent

    async def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to the agent.

        Args:
            data: The message data.

        Returns:
            Response from the agent.
        """
        logger.debug(f"[Mock] Sending to {self._agent_id}: {data}")
        return {"status": "mock_sent", "to": self._agent_id}


class _MockChannelHandle:
    """Handle for posting to a channel."""

    def __init__(self, channel_name: str, source_agent: "TowowBaseAgent"):
        self._channel = channel_name
        self._source = source_agent

    async def post(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post a message to the channel.

        Args:
            data: The message data.

        Returns:
            Response from the channel.
        """
        logger.debug(f"[Mock] Posting to #{self._channel}: {data}")
        return {"status": "mock_posted", "channel": self._channel}

    async def reply(self, message_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Reply to a message in the channel.

        Args:
            message_id: The message to reply to.
            data: The reply data.

        Returns:
            Response from the channel.
        """
        logger.debug(f"[Mock] Replying to {message_id} in #{self._channel}: {data}")
        return {"status": "mock_replied", "channel": self._channel, "reply_to": message_id}


class TowowBaseAgent(ABC):
    """ToWow基础Agent类，所有Agent继承此类.

    提供独立的基类实现，不依赖外部openagents包的特定类。
    """

    def __init__(self, db: Any = None, llm_service: Any = None, **kwargs: Any):
        """Initialize the base agent.

        Args:
            db: Database session or connection.
            llm_service: LLM service for AI completions.
            **kwargs: Additional arguments.
        """
        self.db = db
        self.llm = llm_service
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}")
        self._workspace = _MockWorkspace(self)

    def workspace(self) -> _MockWorkspace:
        """Get the workspace for this agent.

        Returns:
            The workspace instance.
        """
        return self._workspace

    async def on_startup(self) -> None:
        """Agent启动时调用."""
        self._logger.info("Agent started")

    async def on_shutdown(self) -> None:
        """Agent关闭时调用."""
        self._logger.info("Agent shutting down")

    async def on_direct(self, context: EventContext) -> None:
        """处理直接消息，子类应重写.

        Args:
            context: The event context.
        """
        message = context.incoming_event.payload.get("content", {})
        self._logger.debug(f"Received direct message: {message}")

    async def on_channel_post(self, context: ChannelMessageContext) -> None:
        """处理Channel消息，子类应重写.

        Args:
            context: The channel message context.
        """
        message = context.incoming_event.payload.get("content", {})
        self._logger.debug(f"Received channel message in {context.channel}")

    # 便捷方法
    async def send_to_agent(self, agent_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息给指定Agent.

        Args:
            agent_id: Target agent ID.
            data: Message data.

        Returns:
            Response from the agent.
        """
        ws = self.workspace()
        return await ws.agent(agent_id).send(data)

    async def post_to_channel(self, channel: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """向Channel发送消息.

        Args:
            channel: Channel name (with or without #).
            data: Message data.

        Returns:
            Response from the channel.
        """
        ws = self.workspace()
        channel_name = channel.lstrip("#")
        return await ws.channel(channel_name).post(data)

    async def reply_in_channel(
        self, channel: str, message_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """回复Channel中的特定消息.

        Args:
            channel: Channel name (with or without #).
            message_id: Message to reply to.
            data: Reply data.

        Returns:
            Response from the channel.
        """
        ws = self.workspace()
        channel_name = channel.lstrip("#")
        return await ws.channel(channel_name).reply(message_id, data)

    async def get_online_agents(self) -> List[str]:
        """获取在线Agent列表.

        Returns:
            List of agent IDs.
        """
        ws = self.workspace()
        return await ws.list_agents()

    async def get_channels(self) -> List[str]:
        """获取Channel列表.

        Returns:
            List of channel names.
        """
        ws = self.workspace()
        return await ws.channels()
