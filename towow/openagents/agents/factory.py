"""
Agent工厂 - 创建和管理Agent实例
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .coordinator import CoordinatorAgent
from .channel_admin import ChannelAdminAgent
from .user_agent import UserAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Agent工厂

    负责创建和缓存Agent实例
    """

    def __init__(
        self,
        db: Any = None,
        llm_service: Any = None,
        secondme_service: Any = None,
    ):
        """Initialize the agent factory.

        Args:
            db: Database session or connection.
            llm_service: LLM service for AI completions.
            secondme_service: SecondMe service for user digital twins.
        """
        self.db = db
        self.llm = llm_service
        self.secondme = secondme_service
        self._user_agents: Dict[str, UserAgent] = {}
        self._coordinator: Optional[CoordinatorAgent] = None
        self._channel_admin: Optional[ChannelAdminAgent] = None

    def get_coordinator(self) -> CoordinatorAgent:
        """获取Coordinator Agent（单例）.

        Returns:
            The coordinator agent instance.
        """
        if self._coordinator is None:
            self._coordinator = CoordinatorAgent(
                agent_id="coordinator",
                name="Coordinator",
            )
            logger.info("Created Coordinator Agent")
        return self._coordinator

    def get_channel_admin(self) -> ChannelAdminAgent:
        """获取ChannelAdmin Agent（单例）.

        Returns:
            The channel admin agent instance.
        """
        if self._channel_admin is None:
            self._channel_admin = ChannelAdminAgent(
                agent_id="channel_admin",
                name="Channel Admin",
            )
            logger.info("Created ChannelAdmin Agent")
        return self._channel_admin

    def get_user_agent(
        self, user_id: str, profile: Optional[Dict[str, Any]] = None
    ) -> UserAgent:
        """获取UserAgent（按用户缓存）.

        Args:
            user_id: The user ID.
            profile: Optional user profile.

        Returns:
            The user agent instance.
        """
        agent_id = f"user_agent_{user_id}"

        if agent_id not in self._user_agents:
            self._user_agents[agent_id] = UserAgent(
                user_id=user_id,
                profile=profile or {},
                db=self.db,
                llm_service=self.llm,
                secondme_service=self.secondme,
            )
            logger.info(f"Created UserAgent for {user_id}")
        elif profile:
            # 更新profile
            self._user_agents[agent_id].profile = profile

        return self._user_agents[agent_id]

    async def load_user_agents_from_db(self) -> None:
        """从数据库加载所有活跃用户的Agent."""
        if not self.db:
            logger.warning("No database connection, skipping user agent loading")
            return

        try:
            from database.services import AgentProfileService

            service = AgentProfileService(self.db)
            profiles = await service.list_active()

            for profile in profiles:
                # Extract user_id from agent profile
                # AgentProfile.id is the agent_id, extract user_id if it follows pattern
                agent_id = profile.id
                if agent_id.startswith("user_agent_"):
                    user_id = agent_id.replace("user_agent_", "")
                else:
                    user_id = agent_id

                self.get_user_agent(
                    user_id=user_id,
                    profile={
                        "display_name": profile.name,
                        "capabilities": profile.capabilities or {},
                        "description": profile.description,
                    },
                )

            logger.info(f"Loaded {len(profiles)} user agents from database")
        except Exception as e:
            logger.error(f"Failed to load user agents: {e}")

    def list_user_agents(self) -> Dict[str, Dict[str, Any]]:
        """列出所有UserAgent.

        Returns:
            Dictionary mapping agent_id to agent status.
        """
        return {
            agent_id: agent.get_status()
            for agent_id, agent in self._user_agents.items()
        }

    def get_all_agents(self) -> Dict[str, Any]:
        """获取所有Agent.

        Returns:
            Dictionary of all agents.
        """
        agents: Dict[str, Any] = {}

        if self._coordinator:
            agents["coordinator"] = self._coordinator
        if self._channel_admin:
            agents["channel_admin"] = self._channel_admin

        agents.update(self._user_agents)

        return agents

    def remove_user_agent(self, user_id: str) -> bool:
        """移除UserAgent.

        Args:
            user_id: The user ID.

        Returns:
            True if agent was removed, False if not found.
        """
        agent_id = f"user_agent_{user_id}"
        if agent_id in self._user_agents:
            del self._user_agents[agent_id]
            logger.info(f"Removed UserAgent for {user_id}")
            return True
        return False

    def clear_all(self) -> None:
        """清除所有Agent实例."""
        self._user_agents.clear()
        self._coordinator = None
        self._channel_admin = None
        logger.info("Cleared all agent instances")


# 全局工厂实例
_agent_factory: Optional[AgentFactory] = None


def init_agent_factory(
    db: Any = None,
    llm_service: Any = None,
    secondme_service: Any = None,
) -> AgentFactory:
    """初始化Agent工厂.

    Args:
        db: Database session or connection.
        llm_service: LLM service for AI completions.
        secondme_service: SecondMe service for user digital twins.

    Returns:
        The initialized agent factory.
    """
    global _agent_factory
    _agent_factory = AgentFactory(
        db=db,
        llm_service=llm_service,
        secondme_service=secondme_service,
    )
    return _agent_factory


def get_agent_factory() -> Optional[AgentFactory]:
    """获取Agent工厂.

    Returns:
        The agent factory instance or None if not initialized.
    """
    return _agent_factory
