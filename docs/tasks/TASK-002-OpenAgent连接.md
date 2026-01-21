# TASK-002：OpenAgent连接

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-002 |
| 所属Phase | Phase 1：基础框架 |
| 依赖 | TASK-001 |
| 预估工作量 | 1天 |
| 状态 | 待开始 |

---

## 任务描述

实现与OpenAgent框架的基础连接，创建可复用的基础Agent类。

---

## 具体工作

### 1. 创建基础Agent类

`openagents/agents/base.py`:

```python
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.event_context import EventContext, ChannelMessageContext
from openagents.models.agent_config import AgentConfig
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TowowBaseAgent(WorkerAgent):
    """ToWow基础Agent类，所有Agent继承此类"""

    def __init__(self, db=None, llm_service=None, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.llm = llm_service
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}")

    async def on_startup(self):
        """Agent启动时调用"""
        self._logger.info(f"Agent started")

    async def on_shutdown(self):
        """Agent关闭时调用"""
        self._logger.info(f"Agent shutting down")

    async def on_direct(self, context: EventContext):
        """处理直接消息，子类应重写"""
        message = context.incoming_event.payload.get('content', {})
        self._logger.debug(f"Received direct message: {message}")

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel消息，子类应重写"""
        message = context.incoming_event.payload.get('content', {})
        self._logger.debug(f"Received channel message in {context.channel}")

    # 便捷方法
    async def send_to_agent(self, agent_id: str, data: Dict[str, Any]):
        """发送消息给指定Agent"""
        ws = self.workspace()
        return await ws.agent(agent_id).send(data)

    async def post_to_channel(self, channel: str, data: Dict[str, Any]):
        """向Channel发送消息"""
        ws = self.workspace()
        channel_name = channel.lstrip("#")  # 移除#前缀（如果有）
        return await ws.channel(channel_name).post(data)

    async def reply_in_channel(self, channel: str, message_id: str, data: Dict[str, Any]):
        """回复Channel中的特定消息"""
        ws = self.workspace()
        channel_name = channel.lstrip("#")
        return await ws.channel(channel_name).reply(message_id, data)

    async def get_online_agents(self) -> list:
        """获取在线Agent列表"""
        ws = self.workspace()
        return await ws.list_agents()

    async def get_channels(self) -> list:
        """获取Channel列表"""
        ws = self.workspace()
        return await ws.channels()
```

### 2. 创建配置管理

`openagents/config.py`:

```python
from pydantic_settings import BaseSettings
from typing import Optional

class OpenAgentConfig(BaseSettings):
    host: str = "localhost"
    http_port: int = 8700
    grpc_port: int = 8600
    use_grpc: bool = True  # 推荐使用gRPC

    @property
    def http_url(self) -> str:
        return f"http://{self.host}:{self.http_port}"

    @property
    def grpc_url(self) -> str:
        return f"{self.host}:{self.grpc_port}"

    class Config:
        env_prefix = "OPENAGENT_"


class AppConfig(BaseSettings):
    env: str = "development"
    debug: bool = True
    anthropic_api_key: str = ""
    database_url: str = ""

    class Config:
        env_file = ".env"


openagent_config = OpenAgentConfig()
app_config = AppConfig()
```

### 3. 创建连接测试脚本

`scripts/test_connection.py`:

```python
import asyncio
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.agent_config import AgentConfig

class TestAgent(WorkerAgent):
    """测试用Agent"""
    default_agent_id = "test-agent"

    async def on_startup(self):
        print("TestAgent started")

    async def on_shutdown(self):
        print("TestAgent shutting down")

async def test_connection():
    """测试OpenAgent连接"""
    agent = TestAgent(
        agent_config=AgentConfig(
            model_name="auto",
            instruction="Test agent for connection verification"
        )
    )

    try:
        # 启动Agent（会自动连接到OpenAgent网络）
        # 注意：start() 是同步方法，会阻塞
        # 这里使用更底层的方式测试
        print("Attempting to connect to OpenAgent...")

        # 使用workspace API进行验证
        ws = agent.workspace()

        # 测试获取Agent列表
        agents = await ws.list_agents()
        print(f"Found {len(agents)} agents online")

        # 测试获取Channel列表
        channels = await ws.channels()
        print(f"Found {len(channels)} channels")

        # 测试发送消息到系统Channel
        await ws.channel("system").post({"type": "test", "message": "Connection test"})
        print("Successfully posted to system channel")

        print("All connection tests passed!")

    except Exception as e:
        print(f"Connection test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_connection())
```

### 3.1 Agent启动示例

```python
# scripts/start_test_agent.py
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.agent_config import AgentConfig

class MyTestAgent(WorkerAgent):
    default_agent_id = "my-test-agent"

    async def on_startup(self):
        ws = self.workspace()
        await ws.channel("general").post({"text": "Hello from MyTestAgent!"})

    async def on_direct(self, context):
        ws = self.workspace()
        text = context.incoming_event.payload.get('content', {}).get('text', '')
        await ws.agent(context.source_id).send({"text": f"You said: {text}"})

# 启动Agent
agent = MyTestAgent(
    agent_config=AgentConfig(
        model_name="auto",
        instruction="A test agent"
    )
)
agent.start(network_host="localhost", network_port=8700)
```

### 4. 创建Agent启动器

`openagents/launcher.py`:

```python
import asyncio
from typing import List, Type, Dict, Any
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.agent_config import AgentConfig
from .config import openagent_config
import logging

logger = logging.getLogger(__name__)

class AgentLauncher:
    """Agent启动管理器"""

    def __init__(self, network_host: str = "localhost", network_port: int = 8700):
        self.agents: List[WorkerAgent] = []
        self.network_host = network_host
        self.network_port = network_port

    def register(self, agent: WorkerAgent):
        """注册Agent"""
        self.agents.append(agent)
        logger.info(f"Registered agent: {agent.default_agent_id}")

    def start_all(self):
        """启动所有Agent（阻塞）"""
        import threading

        threads = []
        for agent in self.agents:
            t = threading.Thread(
                target=agent.start,
                kwargs={
                    "network_host": self.network_host,
                    "network_port": self.network_port
                }
            )
            t.start()
            threads.append(t)
            logger.info(f"Started agent: {agent.default_agent_id}")

        # 等待所有线程
        for t in threads:
            t.join()


# 使用示例
def launch_towow_agents():
    """启动ToWow所有Agent"""
    from agents.coordinator import CoordinatorAgent
    from agents.channel_admin import ChannelAdminAgent

    launcher = AgentLauncher(
        network_host=openagent_config.host,
        network_port=openagent_config.http_port
    )

    # 创建并注册Agent
    coordinator = CoordinatorAgent(
        agent_config=AgentConfig(
            model_name="auto",
            instruction="Coordinator agent for ToWow"
        )
    )
    launcher.register(coordinator)

    channel_admin = ChannelAdminAgent(
        agent_config=AgentConfig(
            model_name="auto",
            instruction="Channel admin agent for ToWow"
        )
    )
    launcher.register(channel_admin)

    # 启动所有Agent
    launcher.start_all()
```

---

## 验收标准

- [ ] `test_connection.py` 运行成功
- [ ] 能够连接到OpenAgent服务
- [ ] 能够获取在线Agent列表
- [ ] 能够获取Channel列表
- [ ] TowowBaseAgent类可正常实例化

---

## 产出物

- `openagents/agents/base.py` - 基础Agent类
- `openagents/config.py` - 配置管理
- `openagents/launcher.py` - Agent启动器
- `scripts/test_connection.py` - 连接测试脚本

---

## 注意事项

1. 确保OpenAgent服务已启动（端口8700/8600）
2. 首次运行可能需要安装浏览器：`playwright install chromium`（如果使用Playwright）
3. 推荐使用gRPC连接（更稳定）

---

**创建时间**: 2026-01-21

> Beads 任务ID：`towow-28h`
