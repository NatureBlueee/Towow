# TASK-004：Coordinator Agent实现

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-004 |
| 所属Phase | Phase 2：核心Agent |
| 依赖 | TASK-002, TASK-003 |
| 预估工作量 | 1.5天 |
| 状态 | 待开始 |

---

## 任务描述

实现中心调度Agent（Coordinator），负责接收需求、智能筛选候选人、创建协商Channel。

---

## 具体工作

### 1. Coordinator核心实现

`openagents/agents/coordinator.py`:

```python
from typing import Dict, Any, List
from .base import TowowBaseAgent
from database.connection import Database
from database.services import AgentProfileService, DemandService
from services.llm import LLMService
import uuid

class CoordinatorAgent(TowowBaseAgent):
    """中心调度Agent"""

    def __init__(self, database: Database, llm_service: LLMService, **kwargs):
        super().__init__(agent_id="coordinator", **kwargs)
        self.db = database
        self.llm = llm_service
        self.active_demands: Dict[str, Dict] = {}

    async def on_startup(self):
        await super().on_startup()
        self.logger.info("Coordinator Agent started, ready to receive demands")

    async def on_direct_message(self, context):
        """处理来自UserAgent的消息"""
        message = context.message
        sender = context.sender

        msg_type = message.get("type")

        if msg_type == "new_demand":
            await self.handle_new_demand(sender, message.get("demand"))
        elif msg_type == "demand_update":
            await self.handle_demand_update(sender, message)
        else:
            self.logger.warning(f"Unknown message type: {msg_type}")

    async def handle_new_demand(self, sender: str, demand: Dict[str, Any]):
        """处理新需求"""
        self.logger.info(f"Received new demand from {sender}")

        # 1. 生成需求ID
        demand_id = str(uuid.uuid4())

        # 2. 存储需求到数据库
        async with self.db.session() as session:
            await DemandService.create(
                session,
                demand_id=demand_id,
                initiator_agent_id=sender,
                raw_input=demand.get("raw_input", ""),
                surface_demand=demand.get("surface_demand", ""),
                deep_understanding=demand.get("deep_understanding", {})
            )

        # 3. 获取所有活跃Agent简介
        async with self.db.session() as session:
            all_agents = await AgentProfileService.get_all_active(session)
            agent_profiles = [
                {
                    "agent_id": a.agent_id,
                    "user_name": a.user_name,
                    "profile_summary": a.profile_summary,
                    "capabilities": a.capabilities,
                    "interests": a.interests,
                    "location": a.location,
                    "availability": a.availability
                }
                for a in all_agents
                if a.agent_id != sender  # 排除需求发起者
            ]

        # 4. 智能筛选候选人
        candidates = await self.smart_filter(demand, agent_profiles)
        self.logger.info(f"Selected {len(candidates)} candidates for demand {demand_id}")

        # 5. 创建协商Channel
        channel_name = f"collab-{demand_id[:8]}"
        await self.create_collaboration_channel(
            channel_name=channel_name,
            demand_id=demand_id,
            demand=demand,
            candidates=candidates
        )

        # 6. 发送邀请
        for candidate in candidates:
            await self.send_collaboration_invite(
                agent_id=candidate["agent_id"],
                channel_name=channel_name,
                demand=demand,
                reason=candidate.get("selection_reason", "")
            )

        # 7. 通知发起者
        await self.send_direct(
            to=sender,
            content={
                "type": "demand_accepted",
                "demand_id": demand_id,
                "channel": channel_name,
                "candidates_count": len(candidates)
            }
        )

        # 8. 记录活跃需求
        self.active_demands[demand_id] = {
            "channel": channel_name,
            "initiator": sender,
            "candidates": candidates
        }

    async def smart_filter(
        self,
        demand: Dict[str, Any],
        agent_profiles: List[Dict]
    ) -> List[Dict]:
        """智能筛选候选Agent"""

        if not agent_profiles:
            return []

        # 准备提示词
        prompt = self._build_filter_prompt(demand, agent_profiles)

        # 调用LLM
        response = await self.llm.complete(
            prompt=prompt,
            system="你是一个智能筛选系统，负责从候选人中选出最可能愿意参与合作的人。"
        )

        # 解析结果
        candidates = self._parse_filter_response(response, agent_profiles)

        # 限制最多20人
        return candidates[:20]

    def _build_filter_prompt(
        self,
        demand: Dict[str, Any],
        agent_profiles: List[Dict]
    ) -> str:
        """构建筛选提示词"""

        profiles_text = "\n\n".join([
            f"Agent: {p['agent_id']}\n"
            f"昵称: {p['user_name']}\n"
            f"简介: {p.get('profile_summary', '无')}\n"
            f"能力: {p.get('capabilities', [])}\n"
            f"兴趣: {p.get('interests', [])}\n"
            f"位置: {p.get('location', '未知')}\n"
            f"可用性: {p.get('availability', '未知')}"
            for p in agent_profiles
        ])

        return f"""
## 需求信息

**表面需求**: {demand.get('surface_demand', demand.get('raw_input', ''))}

**深层理解**:
{demand.get('deep_understanding', {})}

---

## 候选Agent列表

{profiles_text}

---

## 任务

请从上述候选人中选出10-20个最可能愿意参与这个需求的人。

筛选标准（按重要性排序）：
1. **相关性**: 能力、兴趣与需求匹配
2. **可能性**: 基于其背景，可能对这个需求感兴趣
3. **可用性**: 有时间/精力参与

请返回JSON格式：
```json
{{
  "selected": [
    {{
      "agent_id": "xxx",
      "selection_reason": "为什么选这个人",
      "match_score": 0.8
    }}
  ]
}}
```
"""

    def _parse_filter_response(
        self,
        response: str,
        agent_profiles: List[Dict]
    ) -> List[Dict]:
        """解析筛选结果"""
        import json
        import re

        # 尝试提取JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            self.logger.warning("Could not parse filter response, using fallback")
            return agent_profiles[:10]

        try:
            result = json.loads(json_match.group())
            selected = result.get("selected", [])

            # 验证agent_id存在
            valid_ids = {p["agent_id"] for p in agent_profiles}
            return [s for s in selected if s.get("agent_id") in valid_ids]

        except json.JSONDecodeError:
            self.logger.warning("JSON decode error, using fallback")
            return agent_profiles[:10]

    async def create_collaboration_channel(
        self,
        channel_name: str,
        demand_id: str,
        demand: Dict,
        candidates: List[Dict]
    ):
        """创建协商Channel"""
        # 在OpenAgent中创建Channel（如果需要）
        # 存储到数据库
        async with self.db.session() as session:
            from database.models import CollaborationChannel
            channel = CollaborationChannel(
                channel_id=channel_name,
                demand_id=demand_id,
                invited_agents=[c["agent_id"] for c in candidates],
                status="inviting"
            )
            session.add(channel)

    async def send_collaboration_invite(
        self,
        agent_id: str,
        channel_name: str,
        demand: Dict,
        reason: str
    ):
        """发送协作邀请"""
        await self.send_direct(
            to=agent_id,
            content={
                "type": "collaboration_invite",
                "channel": channel_name,
                "demand": demand,
                "selection_reason": reason
            }
        )
```

### 2. 创建LLM服务

`services/llm.py`:

```python
import anthropic
from typing import Optional

class LLMService:
    """LLM服务封装"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """调用LLM生成回复"""
        messages = [{"role": "user", "content": prompt}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages
        )

        return response.content[0].text
```

---

## 验收标准

- [ ] Coordinator能够接收来自UserAgent的需求
- [ ] 能够从数据库获取Agent简介
- [ ] 能够调用LLM进行智能筛选
- [ ] 能够创建协商Channel
- [ ] 能够发送邀请给候选人

---

## 产出物

- `openagents/agents/coordinator.py` - Coordinator Agent实现
- `services/llm.py` - LLM服务封装
- 单元测试

---

## 测试用例

```python
# tests/test_coordinator.py

async def test_handle_new_demand():
    """测试处理新需求"""
    # 准备Mock数据
    # 验证筛选逻辑
    # 验证Channel创建
    pass

async def test_smart_filter():
    """测试智能筛选"""
    # 准备测试数据
    # 验证返回结果格式
    # 验证候选人数量限制
    pass
```

---

**创建时间**: 2026-01-21

> Beads 任务ID：`towow-ahl`
