"""
Agent Router - 实现 Agent 间的消息路由

解决 send_to_agent 只是 Mock 实现的问题。
将消息实际路由到目标 Agent 并调用其 on_direct 方法。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import TowowBaseAgent, EventContext

logger = logging.getLogger(__name__)


class _DirectEvent:
    """Direct event wrapper for agent messages."""

    def __init__(self, data: Dict[str, Any]):
        self.payload = {"content": data}


class AgentRouter:
    """
    Agent 消息路由器

    负责在 Agent 间路由消息，使用 AgentFactory 获取 Agent 实例
    """

    def __init__(self):
        """初始化路由器"""
        # 消息去重：记录正在处理的消息（防止重复处理）
        self._processing_messages: set = set()
        # 最近处理的消息ID（用于幂等性检查）
        self._recent_message_ids: dict = {}  # message_key -> timestamp
        self._max_recent_messages = 1000

    def _generate_message_key(self, from_agent: str, to_agent: str, data: Dict[str, Any]) -> str:
        """生成消息唯一键"""
        msg_type = data.get("type", "unknown")
        channel_id = data.get("channel_id", "")
        # 使用关键字段生成唯一键
        return f"{from_agent}:{to_agent}:{msg_type}:{channel_id}"

    async def route_message(
        self,
        from_agent: str,
        to_agent: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        路由消息到目标 Agent

        Args:
            from_agent: 源 Agent ID
            to_agent: 目标 Agent ID
            data: 消息数据

        Returns:
            路由结果
        """
        import time

        msg_type = data.get("type", "unknown")
        logger.info("[ROUTER] Routing message from=%s to=%s type=%s",
                    from_agent, to_agent, msg_type)

        # 生成消息唯一键用于去重
        message_key = self._generate_message_key(from_agent, to_agent, data)
        current_time = time.time()

        # 清理过期的消息记录（超过 5 秒）
        expired_keys = [
            k for k, t in self._recent_message_ids.items()
            if current_time - t > 5.0
        ]
        for k in expired_keys:
            del self._recent_message_ids[k]

        # 检查是否正在处理或最近已处理
        if message_key in self._processing_messages:
            logger.warning("[ROUTER] Duplicate message detected (processing): %s", message_key)
            return {"status": "duplicate", "reason": "already_processing"}

        if message_key in self._recent_message_ids:
            logger.warning("[ROUTER] Duplicate message detected (recent): %s", message_key)
            return {"status": "duplicate", "reason": "recently_processed"}

        # 标记为正在处理
        self._processing_messages.add(message_key)

        try:
            # 获取 AgentFactory
            from . import get_agent_factory
            factory = get_agent_factory()

            if not factory:
                logger.warning("[ROUTER] AgentFactory not initialized, message not delivered")
                return {"status": "error", "reason": "factory_not_initialized"}

            # 根据目标 ID 获取 Agent 实例
            target_agent = self._get_agent(factory, to_agent)

            if not target_agent:
                logger.warning("[ROUTER] Target agent not found: %s", to_agent)
                return {"status": "error", "reason": "agent_not_found", "agent_id": to_agent}

            # 构造 EventContext 并调用 on_direct
            from .base import EventContext
            event = _DirectEvent(data)
            context = EventContext(incoming_event=event)

            logger.debug("[ROUTER] Calling on_direct for %s", to_agent)

            # 同步等待消息处理完成，避免并发问题
            # 改为 await 而非 create_task，确保消息按顺序处理
            await self._deliver_message(target_agent, context, to_agent)

            # 记录为已处理
            self._recent_message_ids[message_key] = current_time

            # 限制记录数量
            if len(self._recent_message_ids) > self._max_recent_messages:
                oldest_key = min(self._recent_message_ids, key=self._recent_message_ids.get)
                del self._recent_message_ids[oldest_key]

            return {"status": "delivered", "to": to_agent}

        except Exception as e:
            logger.error("[ROUTER] Error routing message: %s", str(e), exc_info=True)
            return {"status": "error", "reason": str(e)}
        finally:
            # 移除正在处理标记
            self._processing_messages.discard(message_key)

    async def _deliver_message(
        self,
        agent: "TowowBaseAgent",
        context: "EventContext",
        agent_id: str
    ) -> None:
        """
        实际投递消息到 Agent

        Args:
            agent: 目标 Agent 实例
            context: 事件上下文
            agent_id: Agent ID（用于日志）
        """
        try:
            await agent.on_direct(context)
            logger.debug("[ROUTER] Message delivered to %s", agent_id)
        except Exception as e:
            logger.error("[ROUTER] Error in agent.on_direct for %s: %s",
                         agent_id, str(e), exc_info=True)

    def _get_agent(self, factory: Any, agent_id: str) -> Any:
        """
        从 Factory 获取 Agent 实例

        Args:
            factory: AgentFactory 实例
            agent_id: Agent ID

        Returns:
            Agent 实例或 None
        """
        # 特殊处理系统 Agent
        if agent_id == "coordinator":
            return factory.get_coordinator()
        elif agent_id == "channel_admin":
            return factory.get_channel_admin()
        elif agent_id.startswith("user_agent_"):
            # 提取 user_id
            user_id = agent_id.replace("user_agent_", "")
            # 从 config 获取 mock profile
            profile = self._get_mock_profile(agent_id)
            return factory.get_user_agent(user_id, profile)
        else:
            logger.warning("[ROUTER] Unknown agent type: %s", agent_id)
            return None

    def _get_mock_profile(self, agent_id: str) -> Dict[str, Any]:
        """
        获取 Mock Agent 的 Profile

        Args:
            agent_id: Agent ID

        Returns:
            Profile 字典
        """
        try:
            from config import MOCK_CANDIDATES

            for candidate in MOCK_CANDIDATES:
                if candidate.get("agent_id") == agent_id:
                    return {
                        "name": candidate.get("display_name", agent_id),
                        "capabilities": candidate.get("capabilities", []),
                        "tags": candidate.get("keywords", []),
                        "expected_role": candidate.get("expected_role", ""),
                        "description": candidate.get("reason", ""),
                    }

            # 没有找到，返回基本 profile
            user_name = agent_id.replace("user_agent_", "").capitalize()
            return {
                "name": user_name,
                "capabilities": [],
                "tags": [],
                "description": "",
            }

        except ImportError:
            logger.warning("[ROUTER] config module not available")
            return {}


# 全局路由器实例
agent_router = AgentRouter()
