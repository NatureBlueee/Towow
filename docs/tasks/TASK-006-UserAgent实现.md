# TASK-006：UserAgent实现

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-006 |
| 所属Phase | Phase 2：核心Agent |
| 依赖 | TASK-002, TASK-007 |
| 预估工作量 | 1天 |
| 状态 | 待开始 |

---

## 任务描述

实现用户代理Agent，负责与SecondMe通信，代表用户在网络中行动。

---

## 具体工作

### 1. UserAgent核心实现

`openagents/agents/user_agent.py`:

```python
from typing import Dict, Any, Optional
from .base import TowowBaseAgent
from services.secondme import SecondMeClient
import aiohttp

class UserAgent(TowowBaseAgent):
    """用户代理Agent"""

    def __init__(
        self,
        agent_id: str,
        user_id: str,
        secondme_client: SecondMeClient,
        **kwargs
    ):
        super().__init__(agent_id=agent_id, **kwargs)
        self.user_id = user_id
        self.secondme = secondme_client

    async def on_startup(self):
        await super().on_startup()
        self.logger.info(f"UserAgent for user {self.user_id} started")

    async def on_direct_message(self, context):
        """处理来自其他Agent的消息"""
        message = context.message
        sender = context.sender

        msg_type = message.get("type")

        if msg_type == "collaboration_invite":
            await self.handle_invite(sender, message)
        elif msg_type == "proposal":
            await self.handle_proposal(sender, message)
        elif msg_type == "demand_accepted":
            await self.handle_demand_accepted(message)
        else:
            self.logger.debug(f"Unknown message type: {msg_type}")

    async def handle_invite(self, sender: str, message: Dict):
        """处理协作邀请"""
        self.logger.info(f"Received collaboration invite from {sender}")

        # 调用SecondMe决定是否参与
        response = await self.secondme.generate_response(
            user_id=self.user_id,
            context={
                "type": "collaboration_invite",
                "demand": message.get("demand"),
                "selection_reason": message.get("selection_reason")
            }
        )

        # 发送回应到Channel
        channel = message.get("channel")
        await self.post_to_channel(
            channel=f"#{channel}",
            content={
                "type": "response",
                "decision": response.get("decision"),
                "contribution": response.get("contribution"),
                "conditions": response.get("conditions", []),
                "reasoning": response.get("reasoning")
            }
        )

        self.logger.info(f"Sent response to {channel}: {response.get('decision')}")

    async def handle_proposal(self, sender: str, message: Dict):
        """处理方案分配"""
        self.logger.info(f"Received proposal from {sender}")

        # 调用SecondMe决定是否接受
        response = await self.secondme.generate_feedback(
            user_id=self.user_id,
            context={
                "type": "proposal_feedback",
                "proposal": message.get("proposal"),
                "my_assignment": message.get("your_assignment")
            }
        )

        # 发送反馈到Channel
        channel = message.get("channel")
        await self.post_to_channel(
            channel=f"#{channel}",
            content={
                "type": "feedback",
                "feedback_type": response.get("feedback_type"),
                "adjustment_request": response.get("adjustment_request"),
                "reasoning": response.get("reasoning")
            }
        )

    async def handle_demand_accepted(self, message: Dict):
        """处理需求被接受的通知"""
        self.logger.info(
            f"Demand accepted. Channel: {message.get('channel')}, "
            f"Candidates: {message.get('candidates_count')}"
        )
        # 可以通知用户界面

    # === 用户主动操作 ===

    async def submit_demand(self, raw_input: str) -> Dict:
        """提交新需求"""
        # 调用SecondMe理解需求
        understanding = await self.secondme.understand_demand(
            user_id=self.user_id,
            raw_input=raw_input
        )

        # 发送给Coordinator
        await self.send_direct(
            to="coordinator",
            content={
                "type": "new_demand",
                "demand": {
                    "raw_input": raw_input,
                    "surface_demand": understanding.get("surface_demand"),
                    "deep_understanding": understanding.get("deep_understanding"),
                    "uncertainties": understanding.get("uncertainties")
                }
            }
        )

        return understanding
```

### 2. UserAgent工厂

`openagents/agents/user_agent_factory.py`:

```python
from typing import Dict
from .user_agent import UserAgent
from services.secondme import SecondMeClient

class UserAgentFactory:
    """UserAgent工厂，管理用户Agent的创建和查找"""

    def __init__(self, secondme_client: SecondMeClient):
        self.secondme = secondme_client
        self.agents: Dict[str, UserAgent] = {}

    async def get_or_create(self, user_id: str) -> UserAgent:
        """获取或创建用户Agent"""
        agent_id = f"user-{user_id}"

        if agent_id not in self.agents:
            agent = UserAgent(
                agent_id=agent_id,
                user_id=user_id,
                secondme_client=self.secondme
            )
            await agent.connect()
            self.agents[agent_id] = agent

        return self.agents[agent_id]

    async def shutdown_all(self):
        """关闭所有Agent"""
        for agent in self.agents.values():
            await agent.disconnect()
        self.agents.clear()
```

### 3. 与API层集成

`api/routers/demand.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from openagents.agents.user_agent_factory import UserAgentFactory

router = APIRouter(prefix="/api/demand", tags=["demand"])

class DemandRequest(BaseModel):
    user_id: str
    raw_input: str

class DemandResponse(BaseModel):
    success: bool
    surface_demand: str
    deep_understanding: dict
    message: str

@router.post("/submit", response_model=DemandResponse)
async def submit_demand(
    request: DemandRequest,
    factory: UserAgentFactory = Depends(get_agent_factory)
):
    """提交新需求"""
    try:
        agent = await factory.get_or_create(request.user_id)
        result = await agent.submit_demand(request.raw_input)

        return DemandResponse(
            success=True,
            surface_demand=result.get("surface_demand", ""),
            deep_understanding=result.get("deep_understanding", {}),
            message="需求已提交，正在寻找合适的协作者"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 验收标准

- [ ] UserAgent能够与SecondMe通信
- [ ] 能够提交需求并转发给Coordinator
- [ ] 能够接收邀请并调用SecondMe决策
- [ ] 能够接收方案并调用SecondMe反馈
- [ ] UserAgentFactory能正确管理多个用户Agent

---

## 产出物

- `openagents/agents/user_agent.py` - UserAgent实现
- `openagents/agents/user_agent_factory.py` - Agent工厂
- `api/routers/demand.py` - API路由
- 单元测试

---

## 消息流转示意

```
用户输入
    ↓
API /demand/submit
    ↓
UserAgent.submit_demand()
    ↓
SecondMe.understand_demand()  ← 提示词1：需求理解
    ↓
UserAgent → Coordinator (new_demand)
    ↓
[筛选过程]
    ↓
Coordinator → UserAgent (collaboration_invite)
    ↓
UserAgent.handle_invite()
    ↓
SecondMe.generate_response()  ← 提示词3：回应生成
    ↓
UserAgent → Channel (response)
```

---

**创建时间**: 2026-01-21
