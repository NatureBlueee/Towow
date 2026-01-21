#!/usr/bin/env python3
"""测试与OpenAgents平台的连接."""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openagents import TowowBaseAgent, openagent_config
from openagents.models.agent_config import AgentConfig
from openagents.models.event_context import EventContext, ChannelMessageContext
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestAgent(TowowBaseAgent):
    """测试用Agent"""

    async def on_startup(self):
        await super().on_startup()
        logger.info("TestAgent is ready!")

    async def on_direct(self, context: EventContext):
        """处理直接消息"""
        await super().on_direct(context)
        message = context.incoming_event.payload.get('content', {})
        logger.info(f"Received direct message: {message}")

        # 回复消息
        await context.reply({"content": {"text": "Hello! I received your message."}})

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel消息"""
        await super().on_channel_post(context)
        message = context.incoming_event.payload.get('content', {})
        logger.info(f"Received channel message in {context.channel}: {message}")


async def test_connection():
    """测试连接"""
    logger.info("=" * 50)
    logger.info("ToWow OpenAgents Connection Test")
    logger.info("=" * 50)
    logger.info(f"OpenAgent Host: {openagent_config.host}")
    logger.info(f"HTTP Port: {openagent_config.http_port}")
    logger.info(f"gRPC Port: {openagent_config.grpc_port}")
    logger.info(f"Use gRPC: {openagent_config.use_grpc}")
    logger.info("=" * 50)

    # 创建Agent配置
    config = AgentConfig(
        agent_id="test-agent",
        name="Test Agent",
        openagent_host=openagent_config.host,
        openagent_grpc_port=openagent_config.grpc_port,
        openagent_http_port=openagent_config.http_port,
        use_grpc=openagent_config.use_grpc,
    )

    # 创建测试Agent
    agent = TestAgent(config=config)

    try:
        logger.info("Starting TestAgent...")
        await agent.start()
        logger.info("TestAgent started successfully!")

        # 获取在线Agent列表
        try:
            agents = await agent.get_online_agents()
            logger.info(f"Online agents: {agents}")
        except Exception as e:
            logger.warning(f"Could not get online agents: {e}")

        # 获取Channel列表
        try:
            channels = await agent.get_channels()
            logger.info(f"Available channels: {channels}")
        except Exception as e:
            logger.warning(f"Could not get channels: {e}")

        logger.info("Connection test successful!")
        logger.info("Press Ctrl+C to stop...")

        # 保持运行
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopping...")
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        raise
    finally:
        await agent.stop()
        logger.info("TestAgent stopped")


def main():
    """主入口"""
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
