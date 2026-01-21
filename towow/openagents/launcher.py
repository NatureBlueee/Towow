"""Agent启动器 - 简化Agent的启动流程."""

import asyncio
import logging
from typing import Type, Optional, List
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.agent_config import AgentConfig
from openagents.config import openagent_config

logger = logging.getLogger(__name__)


class AgentLauncher:
    """Agent启动器，管理Agent的生命周期"""

    def __init__(self):
        self._agents: List[WorkerAgent] = []
        self._running = False

    def register(self, agent: WorkerAgent) -> "AgentLauncher":
        """注册一个Agent实例"""
        self._agents.append(agent)
        logger.info(f"Registered agent: {agent.config.agent_id}")
        return self

    def create_and_register(
        self,
        agent_class: Type[WorkerAgent],
        agent_id: str,
        name: Optional[str] = None,
        **kwargs
    ) -> WorkerAgent:
        """创建并注册Agent"""
        config = AgentConfig(
            agent_id=agent_id,
            name=name or agent_id,
            openagent_host=openagent_config.host,
            openagent_grpc_port=openagent_config.grpc_port,
            openagent_http_port=openagent_config.http_port,
            use_grpc=openagent_config.use_grpc,
        )
        agent = agent_class(config=config, **kwargs)
        self.register(agent)
        return agent

    async def start_all(self):
        """启动所有注册的Agent"""
        if self._running:
            logger.warning("Launcher already running")
            return

        self._running = True
        logger.info(f"Starting {len(self._agents)} agents...")

        tasks = [agent.start() for agent in self._agents]
        await asyncio.gather(*tasks)

        logger.info("All agents started")

    async def stop_all(self):
        """停止所有Agent"""
        if not self._running:
            return

        logger.info("Stopping all agents...")

        tasks = [agent.stop() for agent in self._agents]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._running = False
        logger.info("All agents stopped")

    async def run_forever(self):
        """启动并持续运行直到收到停止信号"""
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
    agent_class: Type[WorkerAgent],
    agent_id: str,
    name: Optional[str] = None,
    **kwargs
) -> WorkerAgent:
    """快速启动单个Agent的便捷函数"""
    config = AgentConfig(
        agent_id=agent_id,
        name=name or agent_id,
        openagent_host=openagent_config.host,
        openagent_grpc_port=openagent_config.grpc_port,
        openagent_http_port=openagent_config.http_port,
        use_grpc=openagent_config.use_grpc,
    )
    agent = agent_class(config=config, **kwargs)
    await agent.start()
    return agent
