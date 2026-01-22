"""
UserAgentFactory - UserAgent 专用工厂

职责：
1. 管理多个用户 Agent 的创建和查找
2. 提供 get_or_create() 获取或创建用户 Agent
3. 提供 shutdown_all() 关闭所有 Agent

与 AgentFactory 的区别：
- AgentFactory: 管理所有类型的 Agent（Coordinator, ChannelAdmin, UserAgent）
- UserAgentFactory: 专注于 UserAgent 的管理，提供更细粒度的控制
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .user_agent import UserAgent

logger = logging.getLogger(__name__)


class UserAgentFactory:
    """
    UserAgent 工厂类

    管理多个用户 Agent 实例的创建、查找和生命周期管理。
    每个用户对应一个 UserAgent 实例，通过 user_id 唯一标识。
    """

    def __init__(
        self,
        db: Any = None,
        llm_service: Any = None,
        secondme_service: Any = None,
    ):
        """初始化 UserAgent 工厂.

        Args:
            db: 数据库会话或连接
            llm_service: LLM 服务（用于 AI 生成）
            secondme_service: SecondMe 服务（用户数字分身）
        """
        self.db = db
        self.llm = llm_service
        self.secondme = secondme_service
        self._agents: Dict[str, UserAgent] = {}
        self._is_shutdown = False
        logger.info("UserAgentFactory initialized")

    def get_or_create(
        self,
        user_id: str,
        profile: Optional[Dict[str, Any]] = None
    ) -> UserAgent:
        """获取或创建用户 Agent.

        如果该用户的 Agent 已存在，返回现有实例（并更新 profile）。
        如果不存在，创建新的 Agent 实例。

        Args:
            user_id: 用户 ID
            profile: 用户档案（可选，包含能力、偏好等）

        Returns:
            UserAgent 实例

        Raises:
            RuntimeError: 如果工厂已关闭
        """
        if self._is_shutdown:
            raise RuntimeError("UserAgentFactory has been shutdown")

        agent_key = f"user_agent_{user_id}"

        if agent_key in self._agents:
            agent = self._agents[agent_key]
            # 更新 profile（如果提供了新的）
            if profile:
                agent.profile.update(profile)
                logger.debug(f"Updated profile for {agent_key}")
            return agent

        # 创建新 Agent
        agent = UserAgent(
            user_id=user_id,
            profile=profile or {},
            db=self.db,
            llm_service=self.llm,
            secondme_service=self.secondme,
        )

        self._agents[agent_key] = agent
        logger.info(f"Created UserAgent for user {user_id}")

        return agent

    def get(self, user_id: str) -> Optional[UserAgent]:
        """获取用户 Agent（如果存在）.

        Args:
            user_id: 用户 ID

        Returns:
            UserAgent 实例，如果不存在返回 None
        """
        agent_key = f"user_agent_{user_id}"
        return self._agents.get(agent_key)

    def get_by_agent_id(self, agent_id: str) -> Optional[UserAgent]:
        """通过 agent_id 获取用户 Agent.

        Args:
            agent_id: Agent ID（格式：user_agent_{user_id}）

        Returns:
            UserAgent 实例，如果不存在返回 None
        """
        return self._agents.get(agent_id)

    def exists(self, user_id: str) -> bool:
        """检查用户 Agent 是否存在.

        Args:
            user_id: 用户 ID

        Returns:
            True 如果存在，否则 False
        """
        agent_key = f"user_agent_{user_id}"
        return agent_key in self._agents

    def remove(self, user_id: str) -> bool:
        """移除用户 Agent.

        Args:
            user_id: 用户 ID

        Returns:
            True 如果成功移除，False 如果不存在
        """
        agent_key = f"user_agent_{user_id}"
        if agent_key in self._agents:
            del self._agents[agent_key]
            logger.info(f"Removed UserAgent for user {user_id}")
            return True
        return False

    def list_agents(self) -> List[UserAgent]:
        """列出所有用户 Agent.

        Returns:
            UserAgent 实例列表
        """
        return list(self._agents.values())

    def list_agent_ids(self) -> List[str]:
        """列出所有 Agent ID.

        Returns:
            Agent ID 列表
        """
        return list(self._agents.keys())

    def list_user_ids(self) -> List[str]:
        """列出所有用户 ID.

        Returns:
            用户 ID 列表
        """
        return [agent.user_id for agent in self._agents.values()]

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Agent 的状态.

        Returns:
            {agent_id: status_dict}
        """
        return {
            agent_id: agent.get_status()
            for agent_id, agent in self._agents.items()
        }

    def count(self) -> int:
        """获取 Agent 数量.

        Returns:
            Agent 数量
        """
        return len(self._agents)

    async def startup_all(self) -> None:
        """启动所有 Agent.

        调用每个 Agent 的 on_startup 方法。
        """
        logger.info(f"Starting up {len(self._agents)} UserAgents")
        for agent_id, agent in self._agents.items():
            try:
                await agent.on_startup()
            except Exception as e:
                logger.error(f"Failed to start {agent_id}: {e}")

    async def shutdown_all(self) -> None:
        """关闭所有 Agent.

        调用每个 Agent 的 on_shutdown 方法，然后清空缓存。
        """
        logger.info(f"Shutting down {len(self._agents)} UserAgents")
        self._is_shutdown = True

        for agent_id, agent in self._agents.items():
            try:
                await agent.on_shutdown()
            except Exception as e:
                logger.error(f"Failed to shutdown {agent_id}: {e}")

        self._agents.clear()
        logger.info("All UserAgents shutdown complete")

    async def load_from_profiles(
        self,
        profiles: List[Dict[str, Any]]
    ) -> int:
        """从档案列表批量创建 Agent.

        Args:
            profiles: 用户档案列表，每个包含 user_id 和其他信息

        Returns:
            成功创建的 Agent 数量
        """
        count = 0
        for profile in profiles:
            user_id = profile.get("user_id")
            if not user_id:
                logger.warning(f"Profile missing user_id: {profile}")
                continue

            try:
                self.get_or_create(user_id=user_id, profile=profile)
                count += 1
            except Exception as e:
                logger.error(f"Failed to create agent for {user_id}: {e}")

        logger.info(f"Loaded {count} UserAgents from profiles")
        return count

    async def load_from_db(self) -> int:
        """从数据库加载所有活跃用户的 Agent.

        Returns:
            成功加载的 Agent 数量
        """
        if not self.db:
            logger.warning("No database connection, skipping user agent loading")
            return 0

        try:
            from database.services import AgentProfileService

            service = AgentProfileService(self.db)
            profiles = await service.list_active()

            count = 0
            for profile in profiles:
                # 从 agent_id 提取 user_id
                agent_id = profile.id
                if agent_id.startswith("user_agent_"):
                    user_id = agent_id.replace("user_agent_", "")
                else:
                    user_id = agent_id

                self.get_or_create(
                    user_id=user_id,
                    profile={
                        "display_name": profile.name,
                        "capabilities": profile.capabilities or {},
                        "description": profile.description,
                    },
                )
                count += 1

            logger.info(f"Loaded {count} UserAgents from database")
            return count

        except ImportError:
            logger.warning("Database services not available")
            return 0
        except Exception as e:
            logger.error(f"Failed to load user agents from database: {e}")
            return 0

    def clear(self) -> None:
        """清空所有 Agent（不调用 shutdown）.

        用于测试或快速重置场景。
        """
        self._agents.clear()
        self._is_shutdown = False
        logger.info("UserAgentFactory cleared")


# 全局工厂实例
_user_agent_factory: Optional[UserAgentFactory] = None


def init_user_agent_factory(
    db: Any = None,
    llm_service: Any = None,
    secondme_service: Any = None,
) -> UserAgentFactory:
    """初始化全局 UserAgent 工厂.

    Args:
        db: 数据库会话或连接
        llm_service: LLM 服务
        secondme_service: SecondMe 服务

    Returns:
        UserAgentFactory 实例
    """
    global _user_agent_factory
    _user_agent_factory = UserAgentFactory(
        db=db,
        llm_service=llm_service,
        secondme_service=secondme_service,
    )
    return _user_agent_factory


def get_user_agent_factory() -> Optional[UserAgentFactory]:
    """获取全局 UserAgent 工厂.

    Returns:
        UserAgentFactory 实例，如果未初始化返回 None
    """
    return _user_agent_factory
