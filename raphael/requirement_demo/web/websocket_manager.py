"""
WebSocket Manager - 管理 WebSocket 连接和消息推送

提供实时消息推送功能：
1. 用户连接管理
2. 消息广播
3. Channel 消息推送
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """连接信息"""
    websocket: WebSocket
    agent_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    subscribed_channels: Set[str] = field(default_factory=set)


class WebSocketManager:
    """
    WebSocket 连接管理器

    管理所有 WebSocket 连接，支持：
    - 按 agent_id 管理连接
    - 按 channel_id 订阅/广播
    - 全局广播
    """

    def __init__(self):
        # agent_id -> ConnectionInfo
        self._connections: Dict[str, ConnectionInfo] = {}
        # channel_id -> Set[agent_id]
        self._channel_subscribers: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, agent_id: str) -> bool:
        """
        接受 WebSocket 连接

        Args:
            websocket: WebSocket 连接
            agent_id: 用户 Agent ID

        Returns:
            是否连接成功
        """
        try:
            await websocket.accept()

            async with self._lock:
                # 如果已有连接，先关闭旧连接
                if agent_id in self._connections:
                    old_conn = self._connections[agent_id]
                    try:
                        await old_conn.websocket.close(code=1000, reason="New connection")
                    except Exception:
                        pass

                self._connections[agent_id] = ConnectionInfo(
                    websocket=websocket,
                    agent_id=agent_id,
                )

            logger.info(f"WebSocket connected: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"WebSocket connect failed: {e}")
            return False

    async def disconnect(self, agent_id: str):
        """断开连接"""
        async with self._lock:
            if agent_id in self._connections:
                conn = self._connections.pop(agent_id)
                # 从所有 channel 取消订阅
                for channel_id in conn.subscribed_channels:
                    if channel_id in self._channel_subscribers:
                        self._channel_subscribers[channel_id].discard(agent_id)

                logger.info(f"WebSocket disconnected: {agent_id}")

    async def subscribe_channel(self, agent_id: str, channel_id: str):
        """订阅 Channel"""
        async with self._lock:
            if agent_id not in self._connections:
                return

            if channel_id not in self._channel_subscribers:
                self._channel_subscribers[channel_id] = set()

            self._channel_subscribers[channel_id].add(agent_id)
            self._connections[agent_id].subscribed_channels.add(channel_id)

            logger.debug(f"Agent {agent_id} subscribed to channel {channel_id}")

    async def unsubscribe_channel(self, agent_id: str, channel_id: str):
        """取消订阅 Channel"""
        async with self._lock:
            if agent_id in self._connections:
                self._connections[agent_id].subscribed_channels.discard(channel_id)

            if channel_id in self._channel_subscribers:
                self._channel_subscribers[channel_id].discard(agent_id)

    async def send_to_agent(self, agent_id: str, message: Dict[str, Any]) -> bool:
        """
        发送消息给指定 Agent

        Args:
            agent_id: 目标 Agent ID
            message: 消息内容

        Returns:
            是否发送成功
        """
        if agent_id not in self._connections:
            return False

        try:
            conn = self._connections[agent_id]
            await conn.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Send to agent {agent_id} failed: {e}")
            # 连接可能已断开，清理
            await self.disconnect(agent_id)
            return False

    async def broadcast_to_channel(
        self,
        channel_id: str,
        message: Dict[str, Any],
        exclude_agent: Optional[str] = None,
    ) -> int:
        """
        广播消息到 Channel

        Args:
            channel_id: Channel ID
            message: 消息内容
            exclude_agent: 排除的 Agent ID（不发送给该 Agent）

        Returns:
            成功发送的数量
        """
        if channel_id not in self._channel_subscribers:
            return 0

        subscribers = self._channel_subscribers[channel_id].copy()
        if exclude_agent:
            subscribers.discard(exclude_agent)

        success_count = 0
        failed_agents = []

        for agent_id in subscribers:
            if await self.send_to_agent(agent_id, message):
                success_count += 1
            else:
                failed_agents.append(agent_id)

        # 清理失败的连接
        for agent_id in failed_agents:
            await self.disconnect(agent_id)

        return success_count

    async def broadcast_all(
        self,
        message: Dict[str, Any],
        exclude_agent: Optional[str] = None,
    ) -> int:
        """
        广播消息给所有连接

        Args:
            message: 消息内容
            exclude_agent: 排除的 Agent ID

        Returns:
            成功发送的数量
        """
        agents = list(self._connections.keys())
        if exclude_agent:
            agents = [a for a in agents if a != exclude_agent]

        success_count = 0
        failed_agents = []

        for agent_id in agents:
            if await self.send_to_agent(agent_id, message):
                success_count += 1
            else:
                failed_agents.append(agent_id)

        # 清理失败的连接
        for agent_id in failed_agents:
            await self.disconnect(agent_id)

        return success_count

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self._connections)

    def get_channel_subscriber_count(self, channel_id: str) -> int:
        """获取 Channel 订阅者数量"""
        return len(self._channel_subscribers.get(channel_id, set()))

    def is_connected(self, agent_id: str) -> bool:
        """检查 Agent 是否已连接"""
        return agent_id in self._connections

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_connections": len(self._connections),
            "total_channels": len(self._channel_subscribers),
            "channels": {
                channel_id: len(subscribers)
                for channel_id, subscribers in self._channel_subscribers.items()
            },
        }


# 全局单例
_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """获取 WebSocketManager 单例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
