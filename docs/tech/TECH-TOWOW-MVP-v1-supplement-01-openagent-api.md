# 技术方案补充01：OpenAgent API正确使用

> 基于OPENAGENTS_DEV_GUIDE.md的API修正

---

## 一、Agent基类修正

### 1.1 错误的写法（原技术方案）

```python
# ❌ 错误
from openagents import Agent

class MyAgent(Agent):
    async def on_direct_message(self, context):
        pass
    async def on_channel_message(self, context):
        pass
```

### 1.2 正确的写法

```python
# ✅ 正确
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.event_context import EventContext, ChannelMessageContext

class TowowBaseAgent(WorkerAgent):
    """ToWow Agent基类"""

    async def on_direct(self, context: EventContext):
        """处理直接消息"""
        pass

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel消息"""
        pass

    async def on_channel_mention(self, context: ChannelMessageContext):
        """处理@提及"""
        pass

    async def on_startup(self):
        """Agent启动后回调"""
        pass

    async def on_shutdown(self):
        """Agent关闭前回调"""
        pass
```

---

## 二、消息发送API修正

### 2.1 错误的写法（原技术方案）

```python
# ❌ 错误
await self.send_direct(to="agent_id", text="message")
await self.post_to_channel(channel="#channel_name", text="message")
```

### 2.2 正确的写法

```python
# ✅ 正确 - 通过workspace() API

# 获取workspace
ws = self.workspace()

# 发送直接消息
await ws.agent("agent_id").send({"text": "message"})

# 发送到Channel
await ws.channel("channel_name").post({"text": "message"})

# 回复Channel中的消息
await ws.channel("channel_name").reply_to_message(
    message_id="msg_123",
    content={"text": "reply content"}
)

# 获取Channel列表
channels = await ws.channels()

# 获取在线Agent列表
agents = await ws.agents()
```

---

## 三、重写后的Agent实现

### 3.1 TowowBaseAgent（基类）

```python
"""
towow/agents/base.py
ToWow Agent基类
"""
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.event_context import EventContext, ChannelMessageContext
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TowowBaseAgent(WorkerAgent):
    """
    ToWow Agent基类

    提供：
    - 统一的消息处理框架
    - 数据库连接
    - LLM调用封装
    - 提示词加载
    """

    def __init__(self, db=None, llm_service=None, prompt_loader=None, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.llm = llm_service
        self.prompts = prompt_loader
        self._message_handlers = {}

    # === 事件处理 ===

    async def on_direct(self, context: EventContext):
        """处理直接消息"""
        message = context.message
        msg_type = message.get("type", "unknown")

        handler = self._message_handlers.get(msg_type)
        if handler:
            await handler(context, message)
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel消息"""
        message = context.message
        channel = context.channel
        msg_type = message.get("type", "unknown")

        handler = self._message_handlers.get(f"channel:{msg_type}")
        if handler:
            await handler(context, message, channel)
        else:
            logger.debug(f"Unhandled channel message type: {msg_type}")

    def register_handler(self, msg_type: str, handler):
        """注册消息处理器"""
        self._message_handlers[msg_type] = handler

    # === 便捷方法 ===

    async def send_to_agent(self, agent_id: str, content: Dict[str, Any]):
        """发送消息给指定Agent"""
        ws = self.workspace()
        return await ws.agent(agent_id).send(content)

    async def post_to_channel(self, channel: str, content: Dict[str, Any]):
        """发送消息到Channel"""
        ws = self.workspace()
        # 移除#前缀（如果有）
        channel_name = channel.lstrip("#")
        return await ws.channel(channel_name).post(content)

    async def get_online_agents(self) -> list:
        """获取在线Agent列表"""
        ws = self.workspace()
        return await ws.agents()

    async def get_channels(self) -> list:
        """获取Channel列表"""
        ws = self.workspace()
        return await ws.channels()

    # === LLM调用 ===

    async def llm_complete(self, prompt: str, system: str = None) -> str:
        """调用LLM"""
        if not self.llm:
            raise RuntimeError("LLM service not configured")
        return await self.llm.complete(prompt=prompt, system=system)

    async def llm_with_prompt(self, prompt_name: str, **kwargs) -> str:
        """使用命名提示词调用LLM"""
        if not self.prompts:
            raise RuntimeError("Prompt loader not configured")

        template = self.prompts.load(prompt_name)
        prompt = template.format(**kwargs)
        return await self.llm_complete(prompt)
```

### 3.2 CoordinatorAgent（修正版）

```python
"""
towow/agents/coordinator.py
中心调度Agent
"""
from .base import TowowBaseAgent
from openagents.models.event_context import EventContext
from typing import Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)


class CoordinatorAgent(TowowBaseAgent):
    """
    中心调度Agent

    职责：
    1. 接收UserAgent转发的需求
    2. 智能筛选候选Agent
    3. 创建协商Channel
    4. 邀请候选人
    """

    async def on_startup(self):
        """启动时初始化"""
        self.active_demands = {}  # demand_id -> demand_info

        # 注册消息处理器
        self.register_handler("new_demand", self._handle_new_demand)

        logger.info(f"CoordinatorAgent started: {self.client.agent_id}")

    async def _handle_new_demand(self, context: EventContext, message: Dict):
        """处理新需求"""
        demand = message.get("demand", {})
        requester_id = context.sender

        logger.info(f"Received new demand from {requester_id}")

        try:
            # 1. 存储需求
            demand_id = await self._store_demand(demand, requester_id)

            # 2. 获取所有活跃Agent简介
            agent_profiles = await self._get_active_profiles()

            # 3. 智能筛选
            candidates = await self._smart_filter(demand, agent_profiles)

            logger.info(f"Filtered {len(candidates)} candidates for demand {demand_id}")

            # 4. 创建协商Channel
            channel_name = f"collab-{demand_id[:8]}"
            await self._create_collaboration_channel(
                channel_name=channel_name,
                demand_id=demand_id,
                candidates=candidates
            )

            # 5. 邀请候选人
            await self._invite_candidates(
                channel_name=channel_name,
                candidates=candidates,
                demand=demand
            )

            # 6. 通知发起者
            await self.send_to_agent(requester_id, {
                "type": "demand_accepted",
                "demand_id": demand_id,
                "channel": channel_name,
                "candidate_count": len(candidates)
            })

        except Exception as e:
            logger.error(f"Error handling demand: {e}")
            await self.send_to_agent(requester_id, {
                "type": "demand_error",
                "error": str(e)
            })

    async def _store_demand(self, demand: Dict, requester_id: str) -> str:
        """存储需求到数据库"""
        async with self.db.session() as session:
            from database.services import DemandService

            db_demand = await DemandService.create(
                session,
                initiator_agent_id=requester_id,
                raw_input=demand.get("raw_input", ""),
                surface_demand=demand.get("surface_demand", ""),
                deep_understanding=demand.get("deep_understanding", {})
            )
            return str(db_demand.demand_id)

    async def _get_active_profiles(self) -> List[Dict]:
        """获取所有活跃Agent的简介"""
        async with self.db.session() as session:
            from database.services import AgentProfileService

            profiles = await AgentProfileService.get_all_active(session)
            return [
                {
                    "agent_id": p.agent_id,
                    "user_name": p.user_name,
                    "profile_summary": p.profile_summary,
                    "location": p.location,
                    "capabilities": p.capabilities,
                    "interests": p.interests,
                    "recent_focus": p.recent_focus,
                    "availability": p.availability
                }
                for p in profiles
            ]

    async def _smart_filter(self, demand: Dict, profiles: List[Dict]) -> List[str]:
        """
        智能筛选候选Agent

        使用提示词2：智能筛选
        """
        if not profiles:
            return []

        # 构建提示词
        profiles_text = json.dumps(profiles, ensure_ascii=False, indent=2)
        demand_text = json.dumps(demand, ensure_ascii=False, indent=2)

        prompt = f"""
你是ToWow网络的智能筛选系统。

## 需求信息
{demand_text}

## 可用Agent列表（共{len(profiles)}人）
{profiles_text}

## 任务
从上述Agent中筛选出10-20个"值得邀请"的候选人。

"值得邀请"意味着：
1. 能力/资源与需求相关
2. 兴趣/关注点与需求匹配
3. 当前状态适合参与（有时间、有精力）

## 输出格式
返回JSON数组，包含被选中的agent_id和选中理由：
```json
[
  {{"agent_id": "xxx", "reason": "选中理由"}},
  ...
]
```

注意：
- 宁可多选几个，不要漏掉明显相关的人
- 每个被选中的人都要有具体理由
- 最多选20人，最少选5人（如果有的话）
"""

        response = await self.llm_complete(
            prompt=prompt,
            system="你是一个智能筛选系统，根据需求匹配合适的协作者。"
        )

        # 解析响应
        try:
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                candidates = json.loads(json_match.group())
                return [c["agent_id"] for c in candidates]
        except Exception as e:
            logger.error(f"Failed to parse filter response: {e}")

        return []

    async def _create_collaboration_channel(
        self,
        channel_name: str,
        demand_id: str,
        candidates: List[str]
    ):
        """创建协商Channel记录"""
        async with self.db.session() as session:
            from database.models import CollaborationChannel

            channel = CollaborationChannel(
                channel_id=channel_name,
                demand_id=demand_id,
                invited_agents=candidates,
                responded_agents=[],
                status="inviting"
            )
            session.add(channel)

    async def _invite_candidates(
        self,
        channel_name: str,
        candidates: List[str],
        demand: Dict
    ):
        """邀请候选人"""
        for agent_id in candidates:
            await self.send_to_agent(agent_id, {
                "type": "collaboration_invite",
                "channel": channel_name,
                "demand": demand,
                "message": f"您被邀请参与协作，请查看需求并决定是否参与。"
            })
            logger.debug(f"Invited {agent_id} to {channel_name}")
```

### 3.3 ChannelAdminAgent（修正版）

```python
"""
towow/agents/channel_admin.py
Channel管理Agent
"""
from .base import TowowBaseAgent
from openagents.models.event_context import ChannelMessageContext
from typing import Dict, Any, List
from enum import Enum
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class ChannelStatus(Enum):
    """Channel状态"""
    INVITING = "inviting"          # 邀请中
    COLLECTING = "collecting"      # 收集回应中
    AGGREGATING = "aggregating"    # 聚合方案中
    FEEDBACK = "feedback"          # 等待反馈
    ADJUSTING = "adjusting"        # 调整方案中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"              # 失败


class ChannelAdminAgent(TowowBaseAgent):
    """
    Channel管理Agent

    职责：
    1. 收集Agent回应
    2. 聚合方案
    3. 分发方案
    4. 处理反馈和调整
    5. 生成最终方案或妥协方案
    """

    async def on_startup(self):
        """启动时初始化"""
        self.channel_states = {}  # channel_id -> ChannelState
        self.response_timeout = 120  # 2分钟收集超时
        self.max_rounds = 5  # 最多5轮协商

        # 注册Channel消息处理器
        self.register_handler("channel:offer_response", self._handle_offer_response)
        self.register_handler("channel:proposal_feedback", self._handle_proposal_feedback)

        logger.info(f"ChannelAdminAgent started: {self.client.agent_id}")

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel消息"""
        message = context.message
        channel = context.channel
        sender = context.sender
        msg_type = message.get("type", "unknown")

        logger.debug(f"Channel {channel} received {msg_type} from {sender}")

        if msg_type == "offer_response":
            await self._handle_offer_response(context, message, channel)
        elif msg_type == "proposal_feedback":
            await self._handle_proposal_feedback(context, message, channel)

    async def initialize_channel(self, channel_id: str, demand: Dict, invited_agents: List[str]):
        """初始化Channel状态"""
        self.channel_states[channel_id] = {
            "status": ChannelStatus.COLLECTING,
            "demand": demand,
            "invited_agents": invited_agents,
            "responses": {},
            "current_proposal": None,
            "proposal_version": 0,
            "round": 0,
            "feedbacks": {}
        }

        # 启动超时计时器
        asyncio.create_task(self._collection_timeout(channel_id))

    async def _collection_timeout(self, channel_id: str):
        """收集超时处理"""
        await asyncio.sleep(self.response_timeout)

        state = self.channel_states.get(channel_id)
        if state and state["status"] == ChannelStatus.COLLECTING:
            logger.info(f"Collection timeout for {channel_id}, proceeding with {len(state['responses'])} responses")
            await self._trigger_aggregation(channel_id)

    async def _handle_offer_response(self, context, message: Dict, channel: str):
        """处理Agent的offer回应"""
        state = self.channel_states.get(channel)
        if not state:
            return

        sender = context.sender
        response = {
            "agent_id": sender,
            "decision": message.get("decision"),  # participate | decline | need_more_info
            "contribution": message.get("contribution"),
            "conditions": message.get("conditions", []),
            "reasoning": message.get("reasoning")
        }

        state["responses"][sender] = response
        logger.info(f"Received response from {sender}: {response['decision']}")

        # 检查是否收集完成
        if len(state["responses"]) >= len(state["invited_agents"]):
            await self._trigger_aggregation(channel)

    async def _trigger_aggregation(self, channel_id: str):
        """触发方案聚合"""
        state = self.channel_states.get(channel_id)
        if not state:
            return

        state["status"] = ChannelStatus.AGGREGATING

        # 筛选愿意参与的人
        participants = {
            agent_id: resp
            for agent_id, resp in state["responses"].items()
            if resp["decision"] == "participate"
        }

        if not participants:
            # 没有人愿意参与
            await self._handle_no_participants(channel_id)
            return

        # 调用LLM聚合方案
        proposal = await self._llm_aggregate(
            demand=state["demand"],
            participants=participants
        )

        state["current_proposal"] = proposal
        state["proposal_version"] += 1
        state["status"] = ChannelStatus.FEEDBACK

        # 分发方案给参与者
        await self._distribute_proposal(channel_id, proposal, list(participants.keys()))

    async def _llm_aggregate(self, demand: Dict, participants: Dict) -> Dict:
        """
        LLM聚合方案

        使用提示词4：方案聚合
        """
        demand_text = json.dumps(demand, ensure_ascii=False, indent=2)
        participants_text = json.dumps(participants, ensure_ascii=False, indent=2)

        prompt = f"""
你是ToWow的方案聚合系统。

## 原始需求
{demand_text}

## 愿意参与的Agent（共{len(participants)}人）
{participants_text}

## 任务
基于需求和参与者的贡献，生成一个初步合作方案。

## 输出格式
```json
{{
  "summary": "方案摘要（一句话）",
  "assignments": [
    {{
      "agent_id": "xxx",
      "role": "角色",
      "responsibility": "具体职责",
      "conditions_accepted": true/false,
      "notes": "备注"
    }}
  ],
  "timeline": "时间安排",
  "open_questions": ["待确认的问题"],
  "confidence": "high/medium/low"
}}
```

注意：
- 尊重每个参与者提出的条件
- 如果有冲突，标注出来而不是隐藏
- 如果需求无法完全满足，诚实说明缺口
"""

        response = await self.llm_complete(
            prompt=prompt,
            system="你是一个方案聚合系统，将多方贡献整合成可行方案。"
        )

        # 解析响应
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Failed to parse aggregation response: {e}")

        return {"summary": "聚合失败", "assignments": [], "confidence": "low"}

    async def _distribute_proposal(self, channel_id: str, proposal: Dict, participants: List[str]):
        """分发方案给参与者"""
        for agent_id in participants:
            # 找到该Agent的分配
            my_assignment = next(
                (a for a in proposal.get("assignments", []) if a["agent_id"] == agent_id),
                None
            )

            await self.send_to_agent(agent_id, {
                "type": "proposal_review",
                "channel": channel_id,
                "proposal": proposal,
                "my_assignment": my_assignment,
                "message": "请查看方案并提供反馈"
            })

    async def _handle_proposal_feedback(self, context, message: Dict, channel: str):
        """处理方案反馈"""
        state = self.channel_states.get(channel)
        if not state:
            return

        sender = context.sender
        feedback = {
            "agent_id": sender,
            "feedback_type": message.get("feedback_type"),  # accept | negotiate | withdraw
            "adjustment_request": message.get("adjustment_request"),
            "reasoning": message.get("reasoning")
        }

        state["feedbacks"][sender] = feedback
        logger.info(f"Received feedback from {sender}: {feedback['feedback_type']}")

        # 检查是否所有人都反馈了
        participants = [
            a["agent_id"]
            for a in state["current_proposal"].get("assignments", [])
        ]

        if len(state["feedbacks"]) >= len(participants):
            await self._process_all_feedbacks(channel)

    async def _process_all_feedbacks(self, channel_id: str):
        """处理所有反馈"""
        state = self.channel_states.get(channel_id)
        if not state:
            return

        feedbacks = state["feedbacks"]

        # 统计反馈
        accepts = [f for f in feedbacks.values() if f["feedback_type"] == "accept"]
        negotiates = [f for f in feedbacks.values() if f["feedback_type"] == "negotiate"]
        withdraws = [f for f in feedbacks.values() if f["feedback_type"] == "withdraw"]

        logger.info(f"Feedback stats: {len(accepts)} accept, {len(negotiates)} negotiate, {len(withdraws)} withdraw")

        if not negotiates and not withdraws:
            # 所有人都接受，方案确定
            await self._finalize_proposal(channel_id)
        elif state["round"] >= self.max_rounds:
            # 达到最大轮次，生成妥协方案
            await self._generate_compromise(channel_id)
        else:
            # 需要调整
            state["round"] += 1
            state["status"] = ChannelStatus.ADJUSTING
            await self._adjust_proposal(channel_id, negotiates, withdraws)

    async def _adjust_proposal(self, channel_id: str, negotiates: List, withdraws: List):
        """
        调整方案

        使用提示词6：方案调整
        """
        state = self.channel_states.get(channel_id)

        current = state["current_proposal"]

        prompt = f"""
你是ToWow的方案调整系统。

## 当前方案
{json.dumps(current, ensure_ascii=False, indent=2)}

## 需要协商的反馈（{len(negotiates)}条）
{json.dumps(negotiates, ensure_ascii=False, indent=2)}

## 退出的参与者（{len(withdraws)}人）
{json.dumps(withdraws, ensure_ascii=False, indent=2)}

## 任务
根据反馈调整方案，尽量满足协商请求，处理退出者的职责。

## 输出格式
与原方案相同的JSON格式，但要更新assignments和notes。
"""

        response = await self.llm_complete(
            prompt=prompt,
            system="你是一个方案调整系统，根据反馈优化合作方案。"
        )

        # 解析并更新
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                new_proposal = json.loads(json_match.group())
                state["current_proposal"] = new_proposal
                state["proposal_version"] += 1
                state["feedbacks"] = {}  # 清空反馈
                state["status"] = ChannelStatus.FEEDBACK

                # 重新分发
                participants = [a["agent_id"] for a in new_proposal.get("assignments", [])]
                await self._distribute_proposal(channel_id, new_proposal, participants)
        except Exception as e:
            logger.error(f"Failed to adjust proposal: {e}")
            await self._generate_compromise(channel_id)

    async def _finalize_proposal(self, channel_id: str):
        """确定最终方案"""
        state = self.channel_states.get(channel_id)
        state["status"] = ChannelStatus.COMPLETED

        # 通知所有参与者
        proposal = state["current_proposal"]
        for assignment in proposal.get("assignments", []):
            await self.send_to_agent(assignment["agent_id"], {
                "type": "proposal_finalized",
                "channel": channel_id,
                "proposal": proposal,
                "my_assignment": assignment,
                "message": "方案已确定，请按计划执行！"
            })

        # 更新数据库
        await self._update_channel_status(channel_id, "completed")

        logger.info(f"Channel {channel_id} completed successfully")

    async def _generate_compromise(self, channel_id: str):
        """
        生成妥协方案

        使用提示词9：妥协方案
        """
        state = self.channel_states.get(channel_id)

        prompt = f"""
你是ToWow的妥协方案生成系统。

## 背景
经过{state['round']}轮协商，仍未达成完全共识。需要生成一个妥协方案。

## 原始需求
{json.dumps(state['demand'], ensure_ascii=False, indent=2)}

## 当前方案
{json.dumps(state['current_proposal'], ensure_ascii=False, indent=2)}

## 最后一轮反馈
{json.dumps(state['feedbacks'], ensure_ascii=False, indent=2)}

## 任务
生成一个妥协方案，说明：
1. 能够达成的部分
2. 无法满足的部分及原因
3. 给用户的建议

## 输出格式
```json
{{
  "achievable": {{
    "summary": "能达成的部分",
    "assignments": [...]
  }},
  "gaps": [
    {{"description": "缺口描述", "reason": "原因"}}
  ],
  "suggestions": ["建议1", "建议2"],
  "overall_completion": 70  // 完成度百分比
}}
```
"""

        response = await self.llm_complete(
            prompt=prompt,
            system="你是一个妥协方案生成系统，在无法完美匹配时提供最佳可行方案。"
        )

        state["status"] = ChannelStatus.COMPLETED

        # 解析并通知
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                compromise = json.loads(json_match.group())

                # 通知发起者
                await self.post_to_channel(channel_id, {
                    "type": "compromise_proposal",
                    "proposal": compromise,
                    "message": "经过多轮协商，以下是最终可行方案"
                })
        except Exception as e:
            logger.error(f"Failed to generate compromise: {e}")

    async def _handle_no_participants(self, channel_id: str):
        """处理无人参与的情况"""
        state = self.channel_states.get(channel_id)
        state["status"] = ChannelStatus.FAILED

        await self.post_to_channel(channel_id, {
            "type": "no_participants",
            "message": "很遗憾，没有Agent愿意参与此次协作。",
            "suggestions": [
                "尝试调整需求范围",
                "扩大搜索地域",
                "降低条件要求"
            ]
        })

    async def _update_channel_status(self, channel_id: str, status: str):
        """更新数据库中的Channel状态"""
        async with self.db.session() as session:
            from sqlalchemy import update
            from database.models import CollaborationChannel

            await session.execute(
                update(CollaborationChannel)
                .where(CollaborationChannel.channel_id == channel_id)
                .values(status=status)
            )
```

### 3.4 UserAgent（修正版）

```python
"""
towow/agents/user_agent.py
用户代理Agent
"""
from .base import TowowBaseAgent
from openagents.models.event_context import EventContext, ChannelMessageContext
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class UserAgent(TowowBaseAgent):
    """
    用户代理Agent

    职责：
    1. 代表用户在OpenAgent网络中存在
    2. 将外部消息转发给Coordinator
    3. 调用SecondMe进行决策
    4. 将结果返回给用户
    """

    def __init__(self, user_id: str, secondme_client, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.secondme = secondme_client
        self.active_channels = {}  # channel_id -> channel_info

    async def on_startup(self):
        """启动时初始化"""
        self.register_handler("collaboration_invite", self._handle_invite)
        self.register_handler("proposal_review", self._handle_proposal_review)
        self.register_handler("proposal_finalized", self._handle_finalized)
        self.register_handler("demand_accepted", self._handle_demand_accepted)
        self.register_handler("demand_error", self._handle_demand_error)

        logger.info(f"UserAgent started for user {self.user_id}: {self.client.agent_id}")

    async def submit_demand(self, raw_input: str) -> Dict:
        """
        提交需求

        1. 调用SecondMe理解需求
        2. 转发给Coordinator
        """
        # 调用SecondMe进行需求理解
        understanding = await self.secondme.understand_demand(
            user_id=self.user_id,
            raw_input=raw_input
        )

        # 构建需求消息
        demand = {
            "raw_input": raw_input,
            "surface_demand": understanding.get("surface_demand"),
            "deep_understanding": understanding.get("deep_understanding"),
            "uncertainties": understanding.get("uncertainties", []),
            "confidence": understanding.get("confidence", "medium")
        }

        # 发送给Coordinator
        await self.send_to_agent("coordinator", {
            "type": "new_demand",
            "demand": demand
        })

        return {"status": "submitted", "demand": demand}

    async def _handle_invite(self, context: EventContext, message: Dict):
        """处理协作邀请"""
        channel = message.get("channel")
        demand = message.get("demand")

        logger.info(f"Received invite to {channel}")

        # 调用SecondMe决定是否参与
        response = await self.secondme.generate_response(
            user_id=self.user_id,
            context={
                "demand": demand,
                "channel": channel
            }
        )

        # 记录Channel
        self.active_channels[channel] = {
            "demand": demand,
            "my_response": response
        }

        # 发送回应到Channel
        await self.post_to_channel(channel, {
            "type": "offer_response",
            "decision": response.get("decision"),
            "contribution": response.get("contribution"),
            "conditions": response.get("conditions", []),
            "reasoning": response.get("reasoning")
        })

    async def _handle_proposal_review(self, context: EventContext, message: Dict):
        """处理方案评审请求"""
        channel = message.get("channel")
        proposal = message.get("proposal")
        my_assignment = message.get("my_assignment")

        logger.info(f"Reviewing proposal for {channel}")

        # 调用SecondMe生成反馈
        feedback = await self.secondme.generate_feedback(
            user_id=self.user_id,
            context={
                "proposal": proposal,
                "my_assignment": my_assignment
            }
        )

        # 发送反馈到Channel
        await self.post_to_channel(channel, {
            "type": "proposal_feedback",
            "feedback_type": feedback.get("feedback_type"),
            "adjustment_request": feedback.get("adjustment_request"),
            "reasoning": feedback.get("reasoning")
        })

    async def _handle_finalized(self, context: EventContext, message: Dict):
        """处理方案确定通知"""
        channel = message.get("channel")
        proposal = message.get("proposal")
        my_assignment = message.get("my_assignment")

        logger.info(f"Proposal finalized for {channel}")

        # 更新本地状态
        if channel in self.active_channels:
            self.active_channels[channel]["final_proposal"] = proposal
            self.active_channels[channel]["my_assignment"] = my_assignment

        # TODO: 通知用户（通过WebSocket/回调）

    async def _handle_demand_accepted(self, context: EventContext, message: Dict):
        """处理需求被接受"""
        demand_id = message.get("demand_id")
        channel = message.get("channel")
        candidate_count = message.get("candidate_count")

        logger.info(f"Demand {demand_id} accepted, {candidate_count} candidates invited")

        # TODO: 通知用户

    async def _handle_demand_error(self, context: EventContext, message: Dict):
        """处理需求错误"""
        error = message.get("error")
        logger.error(f"Demand error: {error}")

        # TODO: 通知用户
```

---

## 四、Agent启动配置

### 4.1 启动脚本

```python
"""
towow/main.py
ToWow服务启动
"""
import asyncio
from openagents import connect
from agents.coordinator import CoordinatorAgent
from agents.channel_admin import ChannelAdminAgent
from agents.user_agent import UserAgent
from database.connection import Database
from services.llm import LLMService
from services.prompt_loader import PromptLoader
from config import settings


async def main():
    # 初始化服务
    db = Database(settings.DATABASE_URL)
    llm = LLMService(api_key=settings.ANTHROPIC_API_KEY)
    prompts = PromptLoader(settings.PROMPTS_DIR)

    # 连接OpenAgent网络
    # 方式1：gRPC（推荐）
    connection = await connect(
        host=settings.OPENAGENT_HOST,
        port=settings.OPENAGENT_GRPC_PORT,
        use_grpc=True
    )

    # 方式2：HTTP
    # connection = await connect(
    #     host=settings.OPENAGENT_HOST,
    #     port=settings.OPENAGENT_HTTP_PORT,
    #     use_grpc=False
    # )

    # 启动系统Agent
    coordinator = CoordinatorAgent(
        agent_id="coordinator",
        db=db,
        llm_service=llm,
        prompt_loader=prompts
    )
    await coordinator.connect(connection)

    channel_admin = ChannelAdminAgent(
        agent_id="channel_admin",
        db=db,
        llm_service=llm,
        prompt_loader=prompts
    )
    await channel_admin.connect(connection)

    print("ToWow system agents started")

    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 五、修正总结

| 项目 | 原错误 | 修正后 |
|------|--------|--------|
| 基类 | `Agent` | `WorkerAgent` |
| 直接消息处理 | `on_direct_message` | `on_direct` |
| Channel消息处理 | `on_channel_message` | `on_channel_post` |
| 发送直接消息 | `send_direct(to, text)` | `workspace().agent(id).send(content)` |
| 发送Channel消息 | `post_to_channel(channel, text)` | `workspace().channel(name).post(content)` |
| Context类型 | 无类型 | `EventContext`, `ChannelMessageContext` |

---

**文档版本**: v1.0
**创建时间**: 2026-01-21
**状态**: 补充完成
