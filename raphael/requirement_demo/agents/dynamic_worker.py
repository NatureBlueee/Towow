#!/usr/bin/env python3
"""
Dynamic Worker Agent for Requirement Demo Network.

This is a configurable Worker Agent template that can be instantiated
for any user with their specific skills and specialties.

Usage:
    worker = DynamicWorkerAgent(
        agent_id="user_12345",
        display_name="张三",
        skills=["python", "react", "api-design"],
        specialties=["web-development", "backend"],
        secondme_id="sm_xxx",  # SecondMe 用户 ID
    )
    await worker.async_start(...)
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add local mods folder to path for requirement_network adapter
_script_dir = Path(__file__).parent.parent
_mods_dir = _script_dir / "mods"
if _mods_dir.exists() and str(_mods_dir) not in sys.path:
    sys.path.insert(0, str(_mods_dir))

from openagents.agents.worker_agent import WorkerAgent, on_event
from openagents.models.event_context import EventContext
from requirement_network import RequirementNetworkAdapter
from openagents.mods.workspace.messaging import ThreadMessagingAgentAdapter

logger = logging.getLogger(__name__)


class DynamicWorkerAgent(WorkerAgent):
    """
    动态 Worker Agent - 可配置的通用 Agent 模板

    每个用户注册后会创建一个这样的 Agent 实例，
    根据用户填写的技能和专长进行配置。
    """

    def __init__(
        self,
        agent_id: str,
        display_name: str,
        skills: List[str],
        specialties: List[str],
        secondme_id: Optional[str] = None,
        bio: Optional[str] = None,
        **kwargs
    ):
        """
        初始化动态 Worker Agent

        Args:
            agent_id: 唯一标识符（如 "user_12345"）
            display_name: 显示名称（如 "张三"）
            skills: 技能列表（如 ["python", "react"]）
            specialties: 专长领域（如 ["web-development"]）
            secondme_id: SecondMe 用户 ID（用于认证）
            bio: 个人简介
        """
        # 设置 default_agent_id 为传入的 agent_id
        self.default_agent_id = agent_id
        super().__init__(agent_id=agent_id, **kwargs)

        # 用户信息
        self.display_name = display_name
        self.skills = skills
        self.specialties = specialties
        self.secondme_id = secondme_id
        self.bio = bio or f"{display_name} 的 AI Agent"

        # 初始化 adapters
        self.requirement_adapter = RequirementNetworkAdapter()
        self.messaging_adapter = ThreadMessagingAgentAdapter()

        # 追踪已加入的频道
        self.joined_channels: set = set()

        logger.info(f"创建动态 Worker: {agent_id} ({display_name})")
        logger.info(f"  技能: {skills}")
        logger.info(f"  专长: {specialties}")

    async def on_startup(self):
        """Agent 启动后的初始化"""
        # 绑定 adapters
        self.requirement_adapter.bind_client(self.client)
        self.requirement_adapter.bind_connector(self.client.connector)
        self.requirement_adapter.bind_agent(self.agent_id)

        self.messaging_adapter.bind_client(self.client)
        self.messaging_adapter.bind_connector(self.client.connector)
        self.messaging_adapter.bind_agent(self.agent_id)

        logger.info(f"Worker Agent '{self.display_name}' ({self.agent_id}) 已启动")

        # 注册能力到 registry
        await self._register_capabilities()

    async def _register_capabilities(self):
        """注册能力到网络"""
        logger.info(f"正在注册能力: {self.skills}")

        result = await self.requirement_adapter.register_capabilities(
            skills=self.skills,
            specialties=self.specialties,
            agent_card={
                "display_name": self.display_name,
                "bio": self.bio,
                "secondme_id": self.secondme_id,
            }
        )

        if result.get("success"):
            logger.info(f"能力注册成功: {self.agent_id}")
        else:
            logger.error(f"能力注册失败: {result.get('error')}")

    def _analyze_task(self, task_description: str, task_type: str) -> Dict[str, Any]:
        """
        分析任务是否匹配自己的技能

        基于技能关键词匹配来决定接受/拒绝/提议
        """
        description_lower = task_description.lower()
        type_lower = task_type.lower()

        # 计算技能匹配度
        skill_matches = sum(
            1 for skill in self.skills
            if skill.lower() in description_lower or skill.lower() in type_lower
        )
        specialty_matches = sum(
            1 for spec in self.specialties
            if spec.lower() in description_lower or spec.lower() in type_lower
        )

        total_matches = skill_matches + specialty_matches * 2  # 专长权重更高

        logger.info(f"任务分析 - 技能匹配: {skill_matches}, 专长匹配: {specialty_matches}")

        if total_matches >= 2:
            # 接受任务
            return {
                "response_type": "accept",
                "message": self._generate_acceptance_message(task_description),
            }
        elif total_matches == 1:
            # 提议 - 部分匹配
            return {
                "response_type": "propose",
                "alternative": f"我可以协助处理与 {', '.join(self.skills[:3])} 相关的部分。",
                "message": "这个任务与我的部分技能相关，我可以参与协作。",
            }
        else:
            # 拒绝 - 不匹配
            return {
                "response_type": "reject",
                "reason": f"这个任务不在我的专业范围内。我的技能是: {', '.join(self.skills[:3])}",
            }

    def _generate_acceptance_message(self, task_description: str) -> str:
        """生成接受任务的消息"""
        return (
            f"我是 {self.display_name}，我接受这个任务！\n"
            f"我的相关技能: {', '.join(self.skills[:3])}\n"
            f"我会尽快开始工作。"
        )

    async def _send_channel_message(self, channel_id: str, message: str):
        """发送频道消息"""
        try:
            await self.messaging_adapter.send_channel_message(
                channel=channel_id,
                text=message,
            )
            logger.info(f"发送消息到频道 {channel_id}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    @on_event("requirement_network.notification.agent_invited")
    async def handle_agent_invited(self, context: EventContext):
        """处理被邀请加入频道的事件"""
        logger.info(f"=== {self.display_name} 收到邀请 ===")
        data = context.incoming_event.payload

        channel_id = data.get("channel_id")
        requirement_text = data.get("requirement_text", "")

        if not channel_id:
            return

        logger.info(f"被邀请到频道: {channel_id}")
        logger.info(f"需求: {requirement_text[:100]}...")

        # 确保能力已注册
        await self._register_capabilities()

        # 加入频道
        result = await self.requirement_adapter.join_requirement_channel(channel_id)

        if result.get("success"):
            self.joined_channels.add(channel_id)
            logger.info(f"成功加入频道 {channel_id}")

            # 发送自我介绍
            await self._send_channel_message(
                channel_id,
                f"大家好！我是 {self.display_name}，"
                f"擅长 {', '.join(self.skills[:3])}。"
                f"很高兴参与这个需求！"
            )
        else:
            logger.error(f"加入频道失败: {result.get('error')}")

    @on_event("requirement_network.notification.task_distributed")
    async def handle_task_distributed(self, context: EventContext):
        """处理任务分发事件"""
        logger.info(f"=== {self.display_name} 收到任务 ===")
        data = context.incoming_event.payload

        channel_id = data.get("channel_id")
        task_id = data.get("task_id")
        task = data.get("task", {})

        task_description = task.get("description", "")
        task_type = task.get("type", "")

        if not channel_id or not task_id:
            return

        logger.info(f"任务 ID: {task_id}")
        logger.info(f"任务类型: {task_type}")
        logger.info(f"任务描述: {task_description[:100]}...")

        # 分析任务
        analysis = self._analyze_task(task_description, task_type)
        response_type = analysis["response_type"]

        logger.info(f"任务分析结果: {response_type}")

        # 响应任务
        if response_type == "accept":
            result = await self.requirement_adapter.respond_to_task(
                channel_id=channel_id,
                task_id=task_id,
                response_type="accept",
                message=analysis["message"],
            )
        elif response_type == "reject":
            result = await self.requirement_adapter.respond_to_task(
                channel_id=channel_id,
                task_id=task_id,
                response_type="reject",
                reason=analysis["reason"],
            )
        else:
            result = await self.requirement_adapter.respond_to_task(
                channel_id=channel_id,
                task_id=task_id,
                response_type="propose",
                alternative=analysis["alternative"],
                message=analysis.get("message", ""),
            )

        if result.get("success"):
            logger.info(f"任务响应成功: {response_type}")
        else:
            logger.error(f"任务响应失败: {result.get('error')}")


# ============ 便捷函数 ============

async def create_and_start_worker(
    agent_id: str,
    display_name: str,
    skills: List[str],
    specialties: List[str],
    secondme_id: Optional[str] = None,
    bio: Optional[str] = None,
    network_host: str = "localhost",
    network_port: int = 8800,
) -> DynamicWorkerAgent:
    """
    创建并启动一个动态 Worker Agent

    这是一个便捷函数，用于快速创建用户的 Agent

    Args:
        agent_id: 唯一标识符
        display_name: 显示名称
        skills: 技能列表
        specialties: 专长列表
        secondme_id: SecondMe ID
        bio: 个人简介
        network_host: 网络主机
        network_port: 网络端口

    Returns:
        已启动的 DynamicWorkerAgent 实例
    """
    worker = DynamicWorkerAgent(
        agent_id=agent_id,
        display_name=display_name,
        skills=skills,
        specialties=specialties,
        secondme_id=secondme_id,
        bio=bio,
    )

    # workers 组的密码哈希
    workers_password_hash = "3588bb7219b1faa3d01f132a0c60a394258ccc3049d8e4a243b737e62524d147"

    await worker.async_start(
        network_host=network_host,
        network_port=network_port,
        password_hash=workers_password_hash,
    )

    return worker


# ============ 测试入口 ============

async def main():
    """测试动态 Worker Agent"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 创建一个测试用户的 Agent
    worker = await create_and_start_worker(
        agent_id="user_test_001",
        display_name="测试用户",
        skills=["python", "fastapi", "react"],
        specialties=["web-development", "api-design"],
        secondme_id="sm_test_001",
        bio="这是一个测试用户的 Agent",
    )

    print(f"\n动态 Worker Agent 已启动!")
    print(f"  Agent ID: {worker.agent_id}")
    print(f"  显示名称: {worker.display_name}")
    print(f"  技能: {worker.skills}")
    print(f"  专长: {worker.specialties}")
    print(f"\n等待任务分配...")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭...")
    finally:
        await worker.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
