# TASK-T04-channeladmin-aggregate

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T04-channeladmin-aggregate.md`
>
> * TASK_ID: TASK-T04
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-23

---

## 关联 Story

- **STORY-04**: ChannelAdmin 方案聚合

---

## 任务描述

实现 ChannelAdmin Agent 的方案聚合功能，负责收集 UserAgent 的响应并通过 LLM 聚合成统一的协作方案。需要处理 `offer` 和 `negotiate` 两种响应类型，并支持幂等消息处理。

### 当前问题

1. `channel_admin.py` 的 `_aggregate_offers()` 方法未实现真实 LLM 调用
2. 无法处理 `negotiate` 类型的响应
3. 没有幂等处理（`message_id` 去重）

### 改造目标

1. 实现真实的 LLM 方案聚合
2. 正确处理 `offer` 和 `negotiate` 两种响应
3. 实现基于 `message_id` 的幂等处理
4. 生成包含角色分配的完整 Proposal

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/openagents/agents/channel_admin.py` | 实现 `_aggregate_offers()` 和幂等处理 |
| `towow/services/llm.py` | 添加聚合专用提示词模板 |

### 关键代码改动

#### 1. ChannelAdmin 方案聚合实现

```python
# towow/openagents/agents/channel_admin.py

from dataclasses import dataclass, field
from typing import Literal, List, Optional, Set, Dict, Any

@dataclass
class Proposal:
    """协商方案"""
    proposal_id: str
    demand_id: str
    version: int

    summary: str
    objective: str
    assignments: List["Assignment"]
    timeline: "Timeline"
    rationale: str

    is_forced: bool = False
    confirmed_participants: List[str] = field(default_factory=list)
    optional_participants: List[str] = field(default_factory=list)

    gaps: List["Gap"] = field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    created_at: str = ""

@dataclass
class Assignment:
    """角色分配"""
    agent_id: str
    display_name: str
    role: str
    responsibility: str
    dependencies: List[str] = field(default_factory=list)
    is_confirmed: bool = True
    notes: str = ""

@dataclass
class ChannelState:
    """Channel 完整状态"""
    channel_id: str
    demand_id: str
    status: "ChannelStatus"

    demand_data: Dict[str, Any]
    candidates: List[Dict[str, Any]]

    responses: Dict[str, "OfferResponse"] = field(default_factory=dict)
    expected_responses: Set[str] = field(default_factory=set)

    current_proposal: Optional[Proposal] = None
    proposal_version: int = 1

    feedback: Dict[str, "ProposalFeedback"] = field(default_factory=dict)

    current_round: int = 1
    max_rounds: int = 5

    accept_count: int = 0
    reject_count: int = 0
    negotiate_count: int = 0
    withdraw_count: int = 0

    # [v4新增] 幂等控制
    processed_message_ids: Set[str] = field(default_factory=set)

    created_at: str = ""
    last_updated_at: str = ""


class ChannelAdminAgent:
    def __init__(self, llm=None, db=None):
        self.llm = llm
        self.db = db
        self._channels: Dict[str, ChannelState] = {}

    async def handle_offer_response(
        self,
        channel_id: str,
        message: Dict[str, Any]
    ) -> None:
        """
        处理 UserAgent 的响应

        [v4] 幂等处理：通过 message_id 去重
        """
        state = self._channels.get(channel_id)
        if not state:
            logger.error(f"Channel {channel_id} 不存在")
            return

        message_id = message.get("message_id")

        # 幂等检查
        if message_id and message_id in state.processed_message_ids:
            logger.info(f"消息 {message_id} 已处理，跳过")
            return

        # 记录已处理
        if message_id:
            state.processed_message_ids.add(message_id)

        # 存储响应
        agent_id = message.get("agent_id")
        response = OfferResponse(
            offer_id=message.get("offer_id", f"offer-{uuid4().hex[:8]}"),
            agent_id=agent_id,
            display_name=message.get("display_name", agent_id),
            demand_id=state.demand_id,
            response_type=message.get("response_type", "offer"),
            decision=message.get("decision", "participate"),
            contribution=message.get("contribution"),
            conditions=message.get("conditions", []),
            negotiation_points=[
                NegotiationPoint(**p)
                for p in message.get("negotiation_points", [])
            ],
            reasoning=message.get("reasoning", ""),
            decline_reason=message.get("decline_reason"),
            confidence=message.get("confidence", 50),
            message_id=message_id,
            submitted_at=message.get("timestamp", datetime.utcnow().isoformat())
        )

        state.responses[agent_id] = response

        # 检查是否收集完成
        if self._is_collection_complete(state):
            await self._aggregate_offers(channel_id)

    def _is_collection_complete(self, state: ChannelState) -> bool:
        """检查响应是否收集完成"""
        # 所有期望的响应都已收到
        return state.expected_responses.issubset(set(state.responses.keys()))

    async def _aggregate_offers(self, channel_id: str) -> None:
        """
        聚合响应生成方案

        [v4] 处理 offer 和 negotiate 两种响应：
        - offer: 直接纳入方案
        - negotiate: 标注协商要点，可能影响角色分配
        """
        state = self._channels[channel_id]

        # 更新状态
        await self._transition_state(
            channel_id,
            ChannelStatus.AGGREGATING,
            "responses_collected"
        )

        # 分类响应
        offers = []
        negotiations = []
        declines = []

        for agent_id, response in state.responses.items():
            if response.decision == "decline":
                declines.append(response)
            elif response.response_type == "negotiate":
                negotiations.append(response)
            else:
                offers.append(response)

        # 构建聚合提示词
        prompt = self._build_aggregation_prompt(
            demand=state.demand_data,
            offers=offers,
            negotiations=negotiations,
            declines=declines
        )

        try:
            result = await self.llm.call(
                prompt=prompt,
                max_tokens=3000,
                response_format="json"
            )

            proposal_data = json.loads(result)

            # 构建 Proposal
            proposal = Proposal(
                proposal_id=f"prop-{uuid4().hex[:8]}",
                demand_id=state.demand_id,
                version=state.proposal_version,
                summary=proposal_data.get("summary", ""),
                objective=proposal_data.get("objective", ""),
                assignments=[
                    Assignment(
                        agent_id=a.get("agent_id"),
                        display_name=a.get("display_name", ""),
                        role=a.get("role", ""),
                        responsibility=a.get("responsibility", ""),
                        dependencies=a.get("dependencies", []),
                        is_confirmed=a.get("is_confirmed", True),
                        notes=a.get("notes", "")
                    )
                    for a in proposal_data.get("assignments", [])
                ],
                timeline=self._parse_timeline(proposal_data.get("timeline", {})),
                rationale=proposal_data.get("rationale", ""),
                gaps=[
                    Gap(**g) for g in proposal_data.get("gaps", [])
                ],
                confidence=proposal_data.get("confidence", "medium"),
                created_at=datetime.utcnow().isoformat()
            )

            state.current_proposal = proposal

        except Exception as e:
            logger.error(f"方案聚合失败: {e}")
            # 使用降级方案
            proposal = self._get_fallback_proposal(state)
            state.current_proposal = proposal

        # 更新状态
        await self._transition_state(
            channel_id,
            ChannelStatus.PROPOSAL_SENT,
            "proposal_generated"
        )

        # 发布 SSE 事件
        self.emit_sse("towow.proposal.distributed", {
            "channel_id": channel_id,
            "demand_id": state.demand_id,
            "proposal_id": proposal.proposal_id,
            "summary": proposal.summary,
            "participants_count": len(proposal.assignments),
            "has_gaps": len(proposal.gaps) > 0,
            "version": proposal.version
        })

        # 分发方案给参与者
        await self._distribute_proposal(channel_id)

    def _build_aggregation_prompt(
        self,
        demand: Dict[str, Any],
        offers: List[OfferResponse],
        negotiations: List[OfferResponse],
        declines: List[OfferResponse]
    ) -> str:
        """构建聚合提示词"""
        offers_text = json.dumps([
            {
                "agent_id": o.agent_id,
                "display_name": o.display_name,
                "contribution": o.contribution,
                "conditions": o.conditions,
                "confidence": o.confidence
            }
            for o in offers
        ], ensure_ascii=False, indent=2)

        negotiations_text = json.dumps([
            {
                "agent_id": n.agent_id,
                "display_name": n.display_name,
                "contribution": n.contribution,
                "negotiation_points": [
                    {"aspect": p.aspect, "desired_value": p.desired_value, "reason": p.reason}
                    for p in n.negotiation_points
                ]
            }
            for n in negotiations
        ], ensure_ascii=False, indent=2)

        return f"""
你是一个协作方案设计师。根据需求和参与者的响应，设计一个完整的协作方案。

## 需求信息
- 表面需求: {demand.get('surface_demand', '')}
- 深层理解: {json.dumps(demand.get('deep_understanding', {}), ensure_ascii=False)}
- 能力标签: {demand.get('capability_tags', [])}

## 愿意参与的响应（offer 类型）
{offers_text}

## 希望协商的响应（negotiate 类型）
{negotiations_text}

## 拒绝参与的人数
{len(declines)} 人

## 你的任务
1. 根据 offer 响应分配角色和职责
2. 考虑 negotiate 响应中的协商要点，尽量满足合理诉求
3. 识别可能的缺口（能力不足的地方）
4. 生成完整的协作方案

## 输出格式 (JSON)
{{
  "summary": "方案一句话描述",
  "objective": "协作目标",
  "assignments": [
    {{
      "agent_id": "agent_001",
      "display_name": "小王",
      "role": "场地负责人",
      "responsibility": "负责场地预订和布置",
      "dependencies": [],
      "is_confirmed": true,
      "notes": "需要确认具体时间"
    }}
  ],
  "timeline": {{
    "start_date": "2026-02-01",
    "end_date": "2026-02-15",
    "milestones": [
      {{"name": "场地确认", "date": "2026-02-03"}}
    ]
  }},
  "rationale": "方案设计理由",
  "gaps": [
    {{
      "capability": "活动主持",
      "description": "缺少主持人",
      "severity": "medium",
      "suggestion": "建议招募或外聘"
    }}
  ],
  "confidence": "high" | "medium" | "low"
}}

请返回 JSON 格式结果：
"""

    def _get_fallback_proposal(self, state: ChannelState) -> Proposal:
        """降级方案（LLM 失败时）"""
        # 简单合并所有 offer
        assignments = []
        for agent_id, response in state.responses.items():
            if response.decision != "decline":
                assignments.append(Assignment(
                    agent_id=agent_id,
                    display_name=response.display_name,
                    role="参与者",
                    responsibility=response.contribution or "待确认",
                    is_confirmed=response.response_type == "offer"
                ))

        return Proposal(
            proposal_id=f"prop-{uuid4().hex[:8]}",
            demand_id=state.demand_id,
            version=state.proposal_version,
            summary="方案聚合中，请稍候确认",
            objective=state.demand_data.get("surface_demand", ""),
            assignments=assignments,
            timeline=Timeline(start_date="待定", end_date="待定", milestones=[]),
            rationale="系统繁忙，使用默认方案",
            confidence="low",
            created_at=datetime.utcnow().isoformat()
        )

    async def _distribute_proposal(self, channel_id: str) -> None:
        """分发方案给参与者"""
        state = self._channels[channel_id]
        proposal = state.current_proposal

        for assignment in proposal.assignments:
            await self.send_to_user_agent(assignment.agent_id, {
                "type": "proposal_review",
                "channel_id": channel_id,
                "demand_id": state.demand_id,
                "proposal": {
                    "proposal_id": proposal.proposal_id,
                    "summary": proposal.summary,
                    "objective": proposal.objective,
                    "version": proposal.version
                },
                "round": state.current_round,
                "max_rounds": state.max_rounds,
                "your_assignment": {
                    "role": assignment.role,
                    "responsibility": assignment.responsibility,
                    "dependencies": assignment.dependencies
                }
            })
```

---

## 接口契约

### 输入（OfferResponseMessage）

参见 TASK-T03 的输出格式。

### 输出（ProposalReviewMessage）

```typescript
interface ProposalReviewMessage {
  type: "proposal_review";
  channel_id: string;
  demand_id: string;
  proposal: {
    proposal_id: string;
    summary: string;
    objective: string;
    version: number;
  };
  round: number;
  max_rounds: number;  // 5
  your_assignment?: {
    role: string;
    responsibility: string;
    dependencies: string[];
  };
}
```

---

## 依赖

### 硬依赖
- **T01**: demand.py 重构（需要 T01 提供调用入口）

### 接口依赖
- **T03**: UserAgent 响应生成（聚合逻辑依赖响应格式）

### 被依赖
- **T05**: 多轮协商逻辑
- **T09**: 熔断器测试

---

## 验收标准

- [ ] **AC-1**: 收集完所有响应后自动触发聚合
- [ ] **AC-2**: 正确处理 offer 和 negotiate 两种响应类型
- [ ] **AC-3**: 重复消息（相同 message_id）被幂等处理
- [ ] **AC-4**: 生成的 Proposal 包含完整的角色分配
- [ ] **AC-5**: LLM 失败时使用降级方案
- [ ] **AC-6**: SSE 事件 `towow.proposal.distributed` 被正确发布
- [ ] **AC-7**: 方案分发给所有参与者

### 测试用例

```python
# tests/test_channeladmin_aggregate.py

@pytest.mark.asyncio
async def test_aggregate_offers():
    """测试方案聚合"""
    admin = get_channel_admin()

    # 创建 Channel
    channel_id = "test-channel"
    admin._channels[channel_id] = ChannelState(
        channel_id=channel_id,
        demand_id="d-test",
        status=ChannelStatus.COLLECTING,
        demand_data={"surface_demand": "办聚会"},
        candidates=[],
        expected_responses={"agent1", "agent2"}
    )

    # 提交响应
    await admin.handle_offer_response(channel_id, {
        "agent_id": "agent1",
        "response_type": "offer",
        "decision": "participate",
        "contribution": "提供场地",
        "message_id": "msg-001"
    })

    await admin.handle_offer_response(channel_id, {
        "agent_id": "agent2",
        "response_type": "negotiate",
        "decision": "conditional",
        "contribution": "演讲嘉宾",
        "negotiation_points": [{"aspect": "时间", "desired_value": "工作日"}],
        "message_id": "msg-002"
    })

    # 验证方案生成
    state = admin._channels[channel_id]
    assert state.current_proposal is not None
    assert len(state.current_proposal.assignments) > 0

@pytest.mark.asyncio
async def test_idempotent_handling():
    """测试幂等处理"""
    admin = get_channel_admin()
    channel_id = "test-channel"

    admin._channels[channel_id] = ChannelState(
        channel_id=channel_id,
        demand_id="d-test",
        status=ChannelStatus.COLLECTING,
        demand_data={},
        candidates=[],
        expected_responses={"agent1"}
    )

    # 发送相同消息两次
    msg = {
        "agent_id": "agent1",
        "response_type": "offer",
        "decision": "participate",
        "message_id": "msg-duplicate"
    }

    await admin.handle_offer_response(channel_id, msg)
    await admin.handle_offer_response(channel_id, msg)

    # 验证只处理一次
    state = admin._channels[channel_id]
    assert len(state.responses) == 1

@pytest.mark.asyncio
async def test_fallback_proposal():
    """测试降级方案"""
    admin = get_channel_admin()

    # 模拟 LLM 失败
    with patch.object(admin.llm, "call", side_effect=Exception("LLM error")):
        # ... 触发聚合 ...

        state = admin._channels["test-channel"]
        assert state.current_proposal.confidence == "low"
```

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| 聚合逻辑实现 | 2h |
| 幂等处理 | 0.5h |
| 提示词设计 | 1h |
| 单元测试 | 0.5h |
| **总计** | **4h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 返回格式不符 | 解析失败 | JSON Schema 校验 + 降级方案 |
| 与 T03 响应格式不一致 | 聚合失败 | 接口契约先行，联调验证 |
| 大量响应导致提示词过长 | LLM 调用失败 | 响应摘要 + 分批处理 |

---

## 实现记录

### 实际修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/openagents/agents/channel_admin.py` | 1. 新增 `NegotiationPoint` 数据类<br>2. `ChannelState` 新增 `processed_message_ids` 字段<br>3. 改进 `_handle_offer_response()` 支持 message_id 幂等和 response_type<br>4. 改进 `_aggregate_proposals()` 区分 offer/negotiate<br>5. 新增 v4 方法: `_generate_proposal_v4()`, `_build_aggregation_prompt_v4()`, `_validate_and_enhance_proposal_v4()`, `_get_fallback_proposal_v4()`, `_get_aggregation_system_prompt_v4()`<br>6. 改进 `_distribute_proposal()` 支持 your_assignment 字段 |
| `towow/tests/test_channel_admin.py` | 新增 `TestChannelAdminAggregateT04V4` 测试类，11 个测试用例 |

### 核心实现要点

1. **幂等处理 (AC-3)**
   - `ChannelState` 新增 `processed_message_ids: set` 字段
   - `_handle_offer_response()` 优先检查 `message_id` 是否已处理
   - 同时保留 `agent_id` 去重作为兜底

2. **响应类型区分 (AC-2)**
   - 解析 `response_type` 字段，默认为 `"offer"`
   - 解析 `negotiation_points` 协商要点（negotiate 类型）
   - 响应存储包含完整的类型信息和协商要点

3. **聚合逻辑 (AC-1, AC-4)**
   - `_aggregate_proposals()` 分类响应为 offers/negotiations/declines
   - `_generate_proposal_v4()` 调用新的聚合提示词
   - `_validate_and_enhance_proposal_v4()` 确保所有参与者被分配角色
   - negotiate 类型参与者的 `is_confirmed` 标记为 `False`

4. **降级方案 (AC-5)**
   - `_get_fallback_proposal_v4()` 简单合并所有响应
   - 降级方案标记 `is_fallback: True`, `confidence: "low"`
   - negotiate 类型的角色备注包含协商要点摘要

5. **SSE 事件 (AC-6)**
   - `towow.proposal.distributed` 事件包含: `proposal_id`, `summary`, `participants_count`, `has_gaps`, `version`
   - `towow.offer.submitted` 事件包含 `response_type` 和 `negotiation_summary`

6. **方案分发 (AC-7)**
   - `_distribute_proposal()` 发送给所有 participate/conditional 决策的参与者
   - 每个参与者收到的消息包含 `your_assignment` 字段

### 遇到的问题

1. **问题**: 原有 `_generate_proposal()` 方法不区分 offer/negotiate
   - **解决**: 新增 `_generate_proposal_v4()` 方法，保留原方法兼容

2. **问题**: 需要在响应存储中保存更多元数据
   - **解决**: 响应字典新增 `response_type`, `negotiation_points`, `confidence`, `message_id` 字段

---

## 测试记录

### 测试结果

```
======================== 54 passed, 7 warnings in 0.06s ========================
```

### 新增测试用例 (11 个)

| 测试用例 | 验收标准 | 结果 |
|----------|----------|------|
| `test_idempotent_handling_by_message_id` | AC-3 | PASSED |
| `test_offer_response_type_processing` | AC-2 | PASSED |
| `test_negotiate_response_type_processing` | AC-2 | PASSED |
| `test_aggregate_after_all_responses_collected` | AC-1 | PASSED |
| `test_fallback_proposal_v4_structure` | AC-5 | PASSED |
| `test_build_aggregation_prompt_v4` | - | PASSED |
| `test_validate_and_enhance_proposal_v4_adds_missing_participants` | AC-4 | PASSED |
| `test_validate_and_enhance_proposal_v4_adds_negotiation_handling` | - | PASSED |
| `test_proposal_distributed_event_v4_format` | AC-6 | PASSED |
| `test_proposal_distributed_to_all_participants` | AC-7 | PASSED |
| `test_your_assignment_included_in_proposal_review` | - | PASSED |

### 验收标准完成情况

- [x] **AC-1**: 收集完所有响应后自动触发聚合
- [x] **AC-2**: 正确处理 offer 和 negotiate 两种响应类型
- [x] **AC-3**: 重复消息（相同 message_id）被幂等处理
- [x] **AC-4**: 生成的 Proposal 包含完整的角色分配
- [x] **AC-5**: LLM 失败时使用降级方案
- [x] **AC-6**: SSE 事件 `towow.proposal.distributed` 被正确发布
- [x] **AC-7**: 方案分发给所有参与者
