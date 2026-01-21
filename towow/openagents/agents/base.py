"""ToWow Base Agent class - 继承自 OpenAgents WorkerAgent."""

from openagents.agents.worker_agent import WorkerAgent
from openagents.models.event_context import EventContext, ChannelMessageContext
from openagents.models.agent_config import AgentConfig
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TowowBaseAgent(WorkerAgent):
    """ToWow基础Agent类，所有Agent继承此类"""

    def __init__(self, db=None, llm_service=None, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.llm = llm_service
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}")

    async def on_startup(self):
        """Agent启动时调用"""
        self._logger.info(f"Agent started")

    async def on_shutdown(self):
        """Agent关闭时调用"""
        self._logger.info(f"Agent shutting down")

    async def on_direct(self, context: EventContext):
        """处理直接消息，子类应重写"""
        message = context.incoming_event.payload.get('content', {})
        self._logger.debug(f"Received direct message: {message}")

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel消息，子类应重写"""
        message = context.incoming_event.payload.get('content', {})
        self._logger.debug(f"Received channel message in {context.channel}")

    # 便捷方法
    async def send_to_agent(self, agent_id: str, data: Dict[str, Any]):
        """发送消息给指定Agent"""
        ws = self.workspace()
        return await ws.agent(agent_id).send(data)

    async def post_to_channel(self, channel: str, data: Dict[str, Any]):
        """向Channel发送消息"""
        ws = self.workspace()
        channel_name = channel.lstrip("#")
        return await ws.channel(channel_name).post(data)

    async def reply_in_channel(self, channel: str, message_id: str, data: Dict[str, Any]):
        """回复Channel中的特定消息"""
        ws = self.workspace()
        channel_name = channel.lstrip("#")
        return await ws.channel(channel_name).reply(message_id, data)

    async def get_online_agents(self) -> list:
        """获取在线Agent列表"""
        ws = self.workspace()
        return await ws.list_agents()

    async def get_channels(self) -> list:
        """获取Channel列表"""
        ws = self.workspace()
        return await ws.channels()
