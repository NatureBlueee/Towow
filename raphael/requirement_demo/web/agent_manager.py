"""
Agent Manager - 管理动态创建的 Worker Agent 生命周期

这个模块负责：
1. 创建新的 Worker Agent（用户注册时）
2. 追踪所有活跃的 Agent
3. 停止/重启 Agent
4. 持久化 Agent 配置
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import sys

# Add parent directory for imports
_current_dir = Path(__file__).parent
_project_dir = _current_dir.parent
if str(_project_dir / "agents") not in sys.path:
    sys.path.insert(0, str(_project_dir / "agents"))
if str(_project_dir / "mods") not in sys.path:
    sys.path.insert(0, str(_project_dir / "mods"))

logger = logging.getLogger(__name__)


@dataclass
class UserAgentConfig:
    """用户 Agent 配置"""
    agent_id: str
    display_name: str
    skills: List[str]
    specialties: List[str]
    secondme_id: Optional[str] = None
    bio: Optional[str] = None
    created_at: str = ""
    is_active: bool = True

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AgentManager:
    """
    Agent 管理器 - 单例模式

    管理所有动态创建的 Worker Agent
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # Agent 配置存储
        self.agents_config: Dict[str, UserAgentConfig] = {}

        # 运行中的 Agent 实例
        self.running_agents: Dict[str, Any] = {}

        # Agent 任务（asyncio tasks）
        self.agent_tasks: Dict[str, asyncio.Task] = {}

        # 配置文件路径
        self.config_dir = Path(__file__).parent.parent / "data"
        self.config_file = self.config_dir / "user_agents.json"

        # 网络配置
        self.network_host = "localhost"
        self.network_port = 8800

        # 加载已保存的配置
        self._load_config()

        logger.info("AgentManager 初始化完成")

    def _load_config(self):
        """从文件加载 Agent 配置"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for agent_id, config_dict in data.items():
                        self.agents_config[agent_id] = UserAgentConfig(**config_dict)
                logger.info(f"加载了 {len(self.agents_config)} 个用户 Agent 配置")
            except Exception as e:
                logger.error(f"加载配置失败: {e}")

    def _save_config(self):
        """保存 Agent 配置到文件"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            data = {
                agent_id: asdict(config)
                for agent_id, config in self.agents_config.items()
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"保存了 {len(data)} 个用户 Agent 配置")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def generate_agent_id(self, secondme_id: str) -> str:
        """根据 SecondMe ID 生成 Agent ID"""
        # 简单的 ID 生成策略
        import hashlib
        hash_suffix = hashlib.md5(secondme_id.encode()).hexdigest()[:8]
        return f"user_{hash_suffix}"

    async def register_user(
        self,
        display_name: str,
        skills: List[str],
        specialties: List[str],
        secondme_id: str,
        bio: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        注册新用户并创建 Agent

        Args:
            display_name: 显示名称
            skills: 技能列表
            specialties: 专长列表
            secondme_id: SecondMe 用户 ID
            bio: 个人简介

        Returns:
            注册结果字典
        """
        async with self._lock:
            # 生成 Agent ID
            agent_id = self.generate_agent_id(secondme_id)

            # 检查是否已存在
            if agent_id in self.agents_config:
                existing = self.agents_config[agent_id]
                return {
                    "success": True,
                    "message": "用户已注册，返回现有信息",
                    "agent_id": agent_id,
                    "display_name": existing.display_name,
                    "is_new": False,
                }

            # 创建配置
            config = UserAgentConfig(
                agent_id=agent_id,
                display_name=display_name,
                skills=skills,
                specialties=specialties,
                secondme_id=secondme_id,
                bio=bio,
            )

            # 保存配置
            self.agents_config[agent_id] = config
            self._save_config()

            # 启动 Agent
            try:
                await self.start_agent(agent_id)
                return {
                    "success": True,
                    "message": "注册成功，Agent 已启动",
                    "agent_id": agent_id,
                    "display_name": display_name,
                    "is_new": True,
                }
            except Exception as e:
                logger.error(f"启动 Agent 失败: {e}")
                return {
                    "success": True,
                    "message": f"注册成功，但 Agent 启动失败: {e}",
                    "agent_id": agent_id,
                    "display_name": display_name,
                    "is_new": True,
                    "agent_started": False,
                }

    async def start_agent(self, agent_id: str) -> bool:
        """
        启动指定的 Agent

        Args:
            agent_id: Agent ID

        Returns:
            是否启动成功
        """
        if agent_id not in self.agents_config:
            logger.error(f"Agent 配置不存在: {agent_id}")
            return False

        if agent_id in self.running_agents:
            logger.info(f"Agent 已在运行: {agent_id}")
            return True

        config = self.agents_config[agent_id]

        try:
            # 动态导入以避免循环依赖
            from dynamic_worker import DynamicWorkerAgent

            # 创建 Agent 实例
            worker = DynamicWorkerAgent(
                agent_id=config.agent_id,
                display_name=config.display_name,
                skills=config.skills,
                specialties=config.specialties,
                secondme_id=config.secondme_id,
                bio=config.bio,
            )

            # workers 组的密码哈希
            workers_password_hash = "3588bb7219b1faa3d01f132a0c60a394258ccc3049d8e4a243b737e62524d147"

            # 启动 Agent（在后台任务中）
            async def run_agent():
                try:
                    await worker.async_start(
                        network_host=self.network_host,
                        network_port=self.network_port,
                        password_hash=workers_password_hash,
                    )
                    # 保持运行
                    while agent_id in self.running_agents:
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Agent {agent_id} 运行出错: {e}")
                finally:
                    await worker.async_stop()

            # 创建后台任务
            task = asyncio.create_task(run_agent())
            self.agent_tasks[agent_id] = task
            self.running_agents[agent_id] = worker

            logger.info(f"Agent {agent_id} ({config.display_name}) 已启动")
            return True

        except Exception as e:
            logger.error(f"启动 Agent {agent_id} 失败: {e}")
            return False

    async def stop_agent(self, agent_id: str) -> bool:
        """
        停止指定的 Agent

        Args:
            agent_id: Agent ID

        Returns:
            是否停止成功
        """
        if agent_id not in self.running_agents:
            logger.info(f"Agent 未在运行: {agent_id}")
            return True

        try:
            # 从运行列表移除（会触发 run_agent 中的循环退出）
            worker = self.running_agents.pop(agent_id, None)

            # 取消任务
            task = self.agent_tasks.pop(agent_id, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            logger.info(f"Agent {agent_id} 已停止")
            return True

        except Exception as e:
            logger.error(f"停止 Agent {agent_id} 失败: {e}")
            return False

    async def start_all_agents(self):
        """启动所有配置的 Agent"""
        logger.info(f"正在启动 {len(self.agents_config)} 个 Agent...")

        for agent_id, config in self.agents_config.items():
            if config.is_active:
                await self.start_agent(agent_id)
                # 稍微延迟，避免同时大量连接
                await asyncio.sleep(0.5)

        logger.info("所有 Agent 启动完成")

    async def stop_all_agents(self):
        """停止所有运行中的 Agent"""
        logger.info(f"正在停止 {len(self.running_agents)} 个 Agent...")

        agent_ids = list(self.running_agents.keys())
        for agent_id in agent_ids:
            await self.stop_agent(agent_id)

        logger.info("所有 Agent 已停止")

    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有 Agent"""
        result = []
        for agent_id, config in self.agents_config.items():
            result.append({
                "agent_id": agent_id,
                "display_name": config.display_name,
                "skills": config.skills,
                "specialties": config.specialties,
                "is_running": agent_id in self.running_agents,
                "created_at": config.created_at,
            })
        return result

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取指定 Agent 的信息"""
        if agent_id not in self.agents_config:
            return None

        config = self.agents_config[agent_id]
        return {
            **asdict(config),
            "is_running": agent_id in self.running_agents,
        }


# 全局单例
_agent_manager: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    """获取 AgentManager 单例"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager
