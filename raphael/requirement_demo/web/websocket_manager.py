"""
WebSocket Manager - 管理 WebSocket 连接和消息推送

提供实时消息推送功能：
1. 用户连接管理（支持同一用户多个连接）
2. 消息广播
3. Channel 消息推送
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """连接信息"""
    websocket: WebSocket
    agent_id: str
    connection_id: str  # 唯一连接 ID
    connected_at: datetime = field(default_factory=datetime.now)
    subscribed_channels: Set[str] = field(default_factory=set)


class WebSocketManager:
    """
    WebSocket 连接管理器

    管理所有 WebSocket 连接，支持：
    - 按 agent_id 管理连接（支持同一 agent 多个连接）
    - 按 channel_id 订阅/广播
    - 全局广播
    """

    def __init__(self):
        # connection_id -> ConnectionInfo
        self._connections: Dict[str, ConnectionInfo] = {}
        # agent_id -> Set[connection_id]
        self._agent_connections: Dict[str, Set[str]] = {}
        # channel_id -> Set[connection_id]
        self._channel_subscribers: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        self._connection_counter = 0

    def _generate_connection_id(self, agent_id: str) -> str:
        """生成唯一连接 ID"""
        self._connection_counter += 1
        return f"{agent_id}_{self._connection_counter}"

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
                connection_id = self._generate_connection_id(agent_id)

                # 创建连接信息
                conn_info = ConnectionInfo(
                    websocket=websocket,
                    agent_id=agent_id,
                    connection_id=connection_id,
                )

                # 存储连接
                self._connections[connection_id] = conn_info

                # 更新 agent -> connections 映射
                if agent_id not in self._agent_connections:
                    self._agent_connections[agent_id] = set()
                self._agent_connections[agent_id].add(connection_id)

                # 将连接 ID 存储在 websocket 对象上，方便后续断开时使用
                websocket.state.connection_id = connection_id

            logger.info(f"WebSocket connected: {agent_id} (conn_id: {connection_id})")
            return True

        except Exception as e:
            logger.error(f"WebSocket connect failed: {e}")
            return False

    async def disconnect(self, agent_id: str, connection_id: str = None):
        """断开连接"""
        async with self._lock:
            # 如果提供了 connection_id，只断开特定连接
            if connection_id and connection_id in self._connections:
                conn = self._connections.pop(connection_id)

                # 从 agent_connections 中移除
                if agent_id in self._agent_connections:
                    self._agent_connections[agent_id].discard(connection_id)
                    if not self._agent_connections[agent_id]:
                        del self._agent_connections[agent_id]

                # 从所有 channel 取消订阅
                for channel_id in conn.subscribed_channels:
                    if channel_id in self._channel_subscribers:
                        self._channel_subscribers[channel_id].discard(connection_id)

                logger.info(f"WebSocket disconnected: {agent_id} (conn_id: {connection_id})")

            # 如果没有提供 connection_id，断开该 agent 的所有连接
            elif agent_id in self._agent_connections:
                conn_ids = list(self._agent_connections[agent_id])
                for conn_id in conn_ids:
                    if conn_id in self._connections:
                        conn = self._connections.pop(conn_id)
                        for channel_id in conn.subscribed_channels:
                            if channel_id in self._channel_subscribers:
                                self._channel_subscribers[channel_id].discard(conn_id)

                del self._agent_connections[agent_id]
                logger.info(f"WebSocket disconnected: {agent_id} (all connections)")

    async def subscribe_channel(self, agent_id: str, channel_id: str, connection_id: str = None):
        """订阅 Channel"""
        async with self._lock:
            if agent_id not in self._agent_connections:
                return

            if channel_id not in self._channel_subscribers:
                self._channel_subscribers[channel_id] = set()

            # 如果提供了 connection_id，只订阅特定连接
            if connection_id and connection_id in self._connections:
                self._channel_subscribers[channel_id].add(connection_id)
                self._connections[connection_id].subscribed_channels.add(channel_id)
            else:
                # 否则订阅该 agent 的所有连接
                for conn_id in self._agent_connections[agent_id]:
                    self._channel_subscribers[channel_id].add(conn_id)
                    if conn_id in self._connections:
                        self._connections[conn_id].subscribed_channels.add(channel_id)

            logger.debug(f"Agent {agent_id} subscribed to channel {channel_id}")

    async def unsubscribe_channel(self, agent_id: str, channel_id: str, connection_id: str = None):
        """取消订阅 Channel"""
        async with self._lock:
            if agent_id not in self._agent_connections:
                return

            # 如果提供了 connection_id，只取消特定连接的订阅
            if connection_id and connection_id in self._connections:
                self._connections[connection_id].subscribed_channels.discard(channel_id)
                if channel_id in self._channel_subscribers:
                    self._channel_subscribers[channel_id].discard(connection_id)
            else:
                # 否则取消该 agent 所有连接的订阅
                for conn_id in self._agent_connections[agent_id]:
                    if conn_id in self._connections:
                        self._connections[conn_id].subscribed_channels.discard(channel_id)
                    if channel_id in self._channel_subscribers:
                        self._channel_subscribers[channel_id].discard(conn_id)

    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """发送消息到指定连接"""
        if connection_id not in self._connections:
            return False

        try:
            conn = self._connections[connection_id]
            await conn.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Send to connection {connection_id} failed: {e}")
            return False

    async def send_to_agent(self, agent_id: str, message: Dict[str, Any]) -> int:
        """
        发送消息给指定 Agent 的所有连接

        Args:
            agent_id: 目标 Agent ID
            message: 消息内容

        Returns:
            成功发送的连接数
        """
        if agent_id not in self._agent_connections:
            return 0

        success_count = 0
        failed_connections = []

        for conn_id in list(self._agent_connections.get(agent_id, [])):
            if await self._send_to_connection(conn_id, message):
                success_count += 1
            else:
                failed_connections.append(conn_id)

        # 清理失败的连接
        for conn_id in failed_connections:
            await self.disconnect(agent_id, conn_id)

        return success_count

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

        # 排除指定 agent 的所有连接
        if exclude_agent and exclude_agent in self._agent_connections:
            for conn_id in self._agent_connections[exclude_agent]:
                subscribers.discard(conn_id)

        success_count = 0
        failed_connections = []

        for conn_id in subscribers:
            if await self._send_to_connection(conn_id, message):
                success_count += 1
            else:
                failed_connections.append(conn_id)

        # 清理失败的连接
        for conn_id in failed_connections:
            if conn_id in self._connections:
                agent_id = self._connections[conn_id].agent_id
                await self.disconnect(agent_id, conn_id)

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
        connections = list(self._connections.keys())

        # 排除指定 agent 的所有连接
        if exclude_agent and exclude_agent in self._agent_connections:
            exclude_conn_ids = self._agent_connections[exclude_agent]
            connections = [c for c in connections if c not in exclude_conn_ids]

        success_count = 0
        failed_connections = []

        for conn_id in connections:
            if await self._send_to_connection(conn_id, message):
                success_count += 1
            else:
                failed_connections.append(conn_id)

        # 清理失败的连接
        for conn_id in failed_connections:
            if conn_id in self._connections:
                agent_id = self._connections[conn_id].agent_id
                await self.disconnect(agent_id, conn_id)

        return success_count

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self._connections)

    def get_agent_connection_count(self, agent_id: str) -> int:
        """获取指定 Agent 的连接数"""
        return len(self._agent_connections.get(agent_id, set()))

    def get_channel_subscriber_count(self, channel_id: str) -> int:
        """获取 Channel 订阅者数量"""
        return len(self._channel_subscribers.get(channel_id, set()))

    def is_connected(self, agent_id: str) -> bool:
        """检查 Agent 是否已连接"""
        return agent_id in self._agent_connections and len(self._agent_connections[agent_id]) > 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_connections": len(self._connections),
            "total_agents": len(self._agent_connections),
            "total_channels": len(self._channel_subscribers),
            "agents": {
                agent_id: len(conn_ids)
                for agent_id, conn_ids in self._agent_connections.items()
            },
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
