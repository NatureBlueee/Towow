"""Agent启动器 - 简化Agent的启动流程."""

import asyncio
import logging
from typing import Any, List, Optional, Type

from .agents.base import TowowBaseAgent

logger = logging.getLogger(__name__)


class AgentConfig:
    """Agent配置类."""

    def __init__(
        self,
        agent_id: str,
        name: Optional[str] = None,
        host: str = "localhost",
        port: int = 8080,
        **kwargs: Any,
    ):
        """Initialize agent config.

        Args:
            agent_id: Unique agent identifier.
            name: Human-readable name.
            host: Server host.
            port: Server port.
            **kwargs: Additional configuration.
        """
        self.agent_id = agent_id
        self.name = name or agent_id
        self.host = host
        self.port = port
        self.extra = kwargs


class AgentLauncher:
    """Agent启动器，管理Agent的生命周期."""

    def __init__(self):
        """Initialize the launcher."""
        self._agents: List[TowowBaseAgent] = []
        self._running = False

    def register(self, agent: TowowBaseAgent) -> "AgentLauncher":
        """注册一个Agent实例.

        Args:
            agent: The agent to register.

        Returns:
            Self for chaining.
        """
        self._agents.append(agent)
        agent_id = getattr(agent, "agent_id", agent.__class__.__name__)
        logger.info(f"Registered agent: {agent_id}")
        return self

    def create_and_register(
        self,
        agent_class: Type[TowowBaseAgent],
        agent_id: str,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> TowowBaseAgent:
        """创建并注册Agent.

        Args:
            agent_class: The agent class to instantiate.
            agent_id: Unique agent identifier.
            name: Human-readable name.
            **kwargs: Additional arguments for the agent.

        Returns:
            The created agent.
        """
        agent = agent_class(**kwargs)
        self.register(agent)
        return agent

    async def start_all(self) -> None:
        """启动所有注册的Agent."""
        if self._running:
            logger.warning("Launcher already running")
            return

        self._running = True
        logger.info(f"Starting {len(self._agents)} agents...")

        tasks = [agent.on_startup() for agent in self._agents]
        await asyncio.gather(*tasks)

        logger.info("All agents started")

    async def stop_all(self) -> None:
        """停止所有Agent."""
        if not self._running:
            return

        logger.info("Stopping all agents...")

        tasks = [agent.on_shutdown() for agent in self._agents]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._running = False
        logger.info("All agents stopped")

    async def run_forever(self) -> None:
        """启动并持续运行直到收到停止信号."""
        await self.start_all()
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop_all()


# 全局启动器实例
launcher = AgentLauncher()


async def quick_start(
    agent_class: Type[TowowBaseAgent],
    agent_id: str,
    name: Optional[str] = None,
    **kwargs: Any,
) -> TowowBaseAgent:
    """快速启动单个Agent的便捷函数.

    Args:
        agent_class: The agent class to instantiate.
        agent_id: Unique agent identifier.
        name: Human-readable name.
        **kwargs: Additional arguments for the agent.

    Returns:
        The started agent.
    """
    agent = agent_class(**kwargs)
    await agent.on_startup()
    return agent
