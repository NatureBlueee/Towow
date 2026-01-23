# TASK-T03-useragent-response

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T03-useragent-response.md`
>
> * TASK_ID: TASK-T03
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-23

---

## 关联 Story

- **STORY-03**: UserAgent 响应生成

---

## 任务描述

实现 UserAgent 的响应生成功能，使其能够根据用户 profile 和需求信息，通过 LLM 生成 `offer` 或 `negotiate` 类型的响应。根据 PRD v4 分析结论，需要**区分 `response_type: "offer" | "negotiate"`**。

### 当前问题

1. `user_agent.py` 的 `_generate_offer()` 方法未实现真实 LLM 调用
2. 响应类型单一，无法区分 offer 和 negotiate
3. 没有 `negotiation_points` 字段支持讨价还价

### 改造目标

1. 实现真实的 LLM 响应生成
2. 支持 `response_type: "offer" | "negotiate"` 两种响应类型
3. negotiate 类型时填充 `negotiation_points` 字段
4. 添加 `message_id` 支持幂等处理

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/openagents/agents/user_agent.py` | 实现 `_generate_offer()` 真实逻辑 |
| `towow/services/llm.py` | 添加响应生成专用提示词模板 |

### 关键代码改动

#### 1. UserAgent 响应生成实现

```python
# towow/openagents/agents/user_agent.py

from dataclasses import dataclass, field
from typing import Literal, List, Optional
from uuid import uuid4

@dataclass
class NegotiationPoint:
    """协商要点"""
    aspect: str           # 协商方面
    current_value: str    # 当前值
    desired_value: str    # 期望值
    reason: str           # 原因

@dataclass
class OfferResponse:
    """Agent 响应"""
    offer_id: str
    agent_id: str
    display_name: str
    demand_id: str

    response_type: Literal["offer", "negotiate"]  # [v4新增]
    decision: Literal["participate", "decline", "conditional"]

    contribution: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    negotiation_points: List[NegotiationPoint] = field(default_factory=list)

    reasoning: str = ""
    decline_reason: Optional[str] = None
    confidence: int = 0

    message_id: str = ""  # [v4新增] 幂等ID
    submitted_at: str = ""


class UserAgent:
    async def _generate_offer(
        self,
        demand: Dict[str, Any],
        round: int = 1,
        filter_reason: str = "",
        match_score: int = 50
    ) -> OfferResponse:
        """
        生成响应（offer 或 negotiate）

        [v4] 新增 response_type 区分：
        - offer: 直接提交方案
        - negotiate: 希望讨价还价，附带修改建议
        """
        message_id = f"msg-{uuid4().hex[:12]}"

        prompt = self._build_response_prompt(
            demand, round, filter_reason, match_score
        )

        try:
            response = await self.llm.call(
                prompt=prompt,
                max_tokens=1500,
                response_format="json"
            )

            result = json.loads(response)

            # 解析响应类型
            response_type = result.get("response_type", "offer")
            decision = result.get("decision", "participate")

            # 构建响应
            offer = OfferResponse(
                offer_id=f"offer-{uuid4().hex[:8]}",
                agent_id=self.user_id,
                display_name=self.profile.get("name", self.user_id),
                demand_id=demand.get("demand_id", ""),
                response_type=response_type,
                decision=decision,
                contribution=result.get("contribution"),
                conditions=result.get("conditions", []),
                reasoning=result.get("reasoning", ""),
                decline_reason=result.get("decline_reason"),
                confidence=result.get("confidence", 50),
                message_id=message_id,
                submitted_at=datetime.utcnow().isoformat()
            )

            # negotiate 类型时填充协商要点
            if response_type == "negotiate":
                negotiation_points = result.get("negotiation_points", [])
                offer.negotiation_points = [
                    NegotiationPoint(
                        aspect=p.get("aspect", ""),
                        current_value=p.get("current_value", ""),
                        desired_value=p.get("desired_value", ""),
                        reason=p.get("reason", "")
                    )
                    for p in negotiation_points
                ]

            return offer

        except Exception as e:
            logger.error(f"响应生成失败: {e}")
            # 降级响应
            return self._get_fallback_response(demand, message_id)

    def _build_response_prompt(
        self,
        demand: Dict[str, Any],
        round: int,
        filter_reason: str,
        match_score: int
    ) -> str:
        """构建响应生成提示词"""
        return f"""
你是一个协作者，需要评估是否参与一个协作需求。

## 你的身份
- 名称: {self.profile.get('name', '未知')}
- 能力: {json.dumps(self.profile.get('capabilities', []), ensure_ascii=False)}
- 偏好: {json.dumps(self.profile.get('preferences', {}), ensure_ascii=False)}

## 需求信息
- 需求描述: {demand.get('surface_demand', '')}
- 深层理解: {json.dumps(demand.get('deep_understanding', {}), ensure_ascii=False)}
- 能力标签: {demand.get('capability_tags', [])}
- 被邀请原因: {filter_reason}
- 匹配度: {match_score}%

## 当前轮次
第 {round} 轮（最多 5 轮）

## 你需要决定

1. **response_type**: 选择响应类型
   - "offer": 直接提交你的方案
   - "negotiate": 你想讨价还价，提出修改建议

2. **decision**: 选择参与决策
   - "participate": 愿意参与
   - "conditional": 有条件参与
   - "decline": 拒绝参与

## 输出格式 (JSON)
{{
  "response_type": "offer" | "negotiate",
  "decision": "participate" | "conditional" | "decline",
  "contribution": "你能提供的具体贡献（如果 decision 不是 decline）",
  "conditions": ["条件1", "条件2"],  // 如果 decision 是 conditional
  "reasoning": "你的决策理由",
  "decline_reason": "拒绝原因（如果 decline）",
  "confidence": 75,  // 0-100 置信度
  "negotiation_points": [  // 如果 response_type 是 negotiate
    {{
      "aspect": "时间安排",
      "current_value": "周末",
      "desired_value": "工作日晚上",
      "reason": "周末有其他安排"
    }}
  ]
}}

请返回 JSON 格式结果：
"""

    def _get_fallback_response(
        self,
        demand: Dict[str, Any],
        message_id: str
    ) -> OfferResponse:
        """降级响应（LLM 失败时）"""
        return OfferResponse(
            offer_id=f"offer-{uuid4().hex[:8]}",
            agent_id=self.user_id,
            display_name=self.profile.get("name", self.user_id),
            demand_id=demand.get("demand_id", ""),
            response_type="offer",
            decision="participate",
            contribution="愿意参与，具体贡献待确认",
            conditions=[],
            reasoning="系统繁忙，默认参与",
            confidence=50,
            message_id=message_id,
            submitted_at=datetime.utcnow().isoformat()
        )
```

#### 2. 消息发送

```python
# towow/openagents/agents/user_agent.py

class UserAgent:
    async def handle_demand_offer(self, message: Dict[str, Any]) -> None:
        """处理需求邀请"""
        channel_id = message.get("channel_id")
        demand = message.get("demand")
        round = message.get("round", 1)
        filter_reason = message.get("filter_reason", "")
        match_score = message.get("match_score", 50)

        # 生成响应
        offer = await self._generate_offer(
            demand=demand,
            round=round,
            filter_reason=filter_reason,
            match_score=match_score
        )

        # 发送响应给 ChannelAdmin
        await self.send_to_channel_admin(channel_id, {
            "type": "offer_response",
            "channel_id": channel_id,
            "agent_id": offer.agent_id,
            "display_name": offer.display_name,
            "response_type": offer.response_type,
            "decision": offer.decision,
            "contribution": offer.contribution,
            "conditions": offer.conditions,
            "reasoning": offer.reasoning,
            "decline_reason": offer.decline_reason,
            "negotiation_points": [
                {
                    "aspect": p.aspect,
                    "current_value": p.current_value,
                    "desired_value": p.desired_value,
                    "reason": p.reason
                }
                for p in offer.negotiation_points
            ],
            "message_id": offer.message_id,
            "timestamp": offer.submitted_at
        })

        # 发布 SSE 事件
        self.emit_sse("towow.offer.submitted", {
            "channel_id": channel_id,
            "demand_id": offer.demand_id,
            "agent_id": offer.agent_id,
            "display_name": offer.display_name,
            "response_type": offer.response_type,
            "decision": offer.decision,
            "contribution": offer.contribution,
            "negotiation_summary": self._summarize_negotiation_points(offer)
        })

    def _summarize_negotiation_points(self, offer: OfferResponse) -> Optional[str]:
        """汇总协商要点"""
        if not offer.negotiation_points:
            return None
        return "; ".join([
            f"{p.aspect}: 期望{p.desired_value}"
            for p in offer.negotiation_points
        ])
```

---

## 接口契约

### 输入（DemandOfferMessage）

```typescript
interface DemandOfferMessage {
  type: "demand_offer";
  channel_id: string;
  demand_id: string;
  demand: {
    surface_demand: string;
    deep_understanding: Record<string, any>;
    capability_tags: string[];
    context: Record<string, any>;
  };
  round: number;
  filter_reason: string;
  match_score: number;
}
```

### 输出（OfferResponseMessage）

```typescript
interface OfferResponseMessage {
  type: "offer_response";
  channel_id: string;
  agent_id: string;
  display_name: string;
  response_type: "offer" | "negotiate";  // [v4新增]
  decision: "participate" | "decline" | "conditional";
  contribution?: string;
  conditions?: string[];
  reasoning: string;
  decline_reason?: string;
  negotiation_points?: NegotiationPoint[];  // [v4新增]
  message_id: string;  // [v4新增]
  timestamp: string;
}

interface NegotiationPoint {
  aspect: string;
  current_value: string;
  desired_value: string;
  reason: string;
}
```

---

## 依赖

### 硬依赖
- **T01**: demand.py 重构（需要 T01 提供调用入口）

### 接口依赖
- **T04**: ChannelAdmin 方案聚合（响应格式需与 T04 对齐）

### 被依赖
- **T05**: 多轮协商逻辑

---

## 验收标准

- [ ] **AC-1**: UserAgent 收到 `demand_offer` 后能生成响应
- [ ] **AC-2**: 响应包含 `response_type` 字段（"offer" 或 "negotiate"）
- [ ] **AC-3**: negotiate 类型时，`negotiation_points` 非空
- [ ] **AC-4**: 响应包含 `message_id` 字段（用于幂等）
- [ ] **AC-5**: LLM 失败时，返回降级响应（默认 participate）
- [ ] **AC-6**: SSE 事件 `towow.offer.submitted` 被正确发布
- [ ] **AC-7**: SSE 事件包含 `negotiation_summary`（如有）

### 测试用例

```python
# tests/test_useragent_response.py

@pytest.mark.asyncio
async def test_generate_offer_response():
    """测试生成 offer 类型响应"""
    agent = UserAgent(
        user_id="test_user",
        profile={"name": "小王", "capabilities": ["场地提供"]}
    )

    demand = {
        "demand_id": "d-test",
        "surface_demand": "办AI聚会",
        "capability_tags": ["场地提供"]
    }

    offer = await agent._generate_offer(demand)

    assert offer.response_type in ["offer", "negotiate"]
    assert offer.decision in ["participate", "decline", "conditional"]
    assert offer.message_id is not None

@pytest.mark.asyncio
async def test_generate_negotiate_response():
    """测试生成 negotiate 类型响应"""
    agent = UserAgent(
        user_id="test_user",
        profile={"name": "小王"}
    )

    # 模拟 LLM 返回 negotiate 类型
    mock_response = {
        "response_type": "negotiate",
        "decision": "conditional",
        "negotiation_points": [
            {"aspect": "时间", "current_value": "周末", "desired_value": "工作日", "reason": "周末忙"}
        ]
    }

    with patch.object(agent.llm, "call", return_value=json.dumps(mock_response)):
        offer = await agent._generate_offer({"demand_id": "d-test"})

        assert offer.response_type == "negotiate"
        assert len(offer.negotiation_points) == 1
        assert offer.negotiation_points[0].aspect == "时间"

@pytest.mark.asyncio
async def test_fallback_response():
    """测试降级响应"""
    agent = UserAgent(user_id="test_user", profile={})

    # 模拟 LLM 失败
    with patch.object(agent.llm, "call", side_effect=Exception("LLM error")):
        offer = await agent._generate_offer({"demand_id": "d-test"})

        assert offer.response_type == "offer"
        assert offer.decision == "participate"
        assert offer.confidence == 50
```

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| 响应生成实现 | 2h |
| 提示词设计 | 1h |
| 降级逻辑 | 0.5h |
| 单元测试 | 0.5h |
| **总计** | **4h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 返回格式不符 | 解析失败 | JSON Schema 校验 + 降级响应 |
| 响应质量差 | 协商效果不佳 | 优化提示词，增加示例 |
| 与 T04 接口不一致 | 聚合失败 | 先定义接口契约，联调验证 |

---

## 实现记录

### 实际修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/openagents/agents/user_agent.py` | 核心实现文件，新增数据类和方法 |
| `towow/tests/test_user_agent.py` | 新增 v4 特性测试用例 |

### 关键代码改动

#### 1. 新增数据类定义（v4）

```python
@dataclass
class NegotiationPoint:
    """协商要点 - 当 response_type 为 negotiate 时使用."""
    aspect: str           # 协商方面
    current_value: str    # 当前值
    desired_value: str    # 期望值
    reason: str           # 调整原因

@dataclass
class OfferResponse:
    """Agent 响应 - v4 完整响应结构."""
    offer_id: str
    agent_id: str
    display_name: str
    demand_id: str
    response_type: Literal["offer", "negotiate"]  # [v4新增]
    decision: Literal["participate", "decline", "conditional"]
    # ... 其他字段
    negotiation_points: List[NegotiationPoint]  # [v4新增]
    message_id: str  # [v4新增] 幂等ID
```

#### 2. 更新 `_llm_generate_response` 方法

- 生成幂等 `message_id`
- 更新提示词支持 `response_type` 和 `negotiation_points`
- 错误时调用 `_get_fallback_response`

#### 3. 更新 `_parse_response` 方法

- 解析 `response_type` 字段，默认为 "offer"
- 解析 `negotiation_points` 数组
- 仅当 `response_type == "negotiate"` 时填充 negotiation_points

#### 4. 新增辅助方法

- `_get_fallback_response()`: 降级响应，包含 message_id
- `_summarize_negotiation_points()`: 汇总协商要点
- `_emit_offer_submitted_event()`: 发布 SSE 事件

#### 5. 更新 `_handle_demand_offer` 方法

- 支持 v4 消息格式
- 发布 `towow.offer.submitted` SSE 事件
- 包含 `negotiation_summary` 字段

### 遇到的问题

1. **事件总线 import 路径**: events 模块在 `towow.events` 下而非 `openagents.events`，需要使用绝对导入。

### 解决方案

使用 `from towow.events.bus import event_bus, Event` 绝对导入。

---

## 测试记录

### 测试结果

```
33 passed, 3 warnings in 0.05s
```

### 新增测试用例

| 测试类 | 测试数量 | 说明 |
|--------|----------|------|
| TestUserAgentV4ResponseType | 7 | response_type、negotiation_points 解析测试 |
| TestNegotiationPointDataclass | 1 | NegotiationPoint.to_dict() 测试 |
| TestOfferResponseDataclass | 1 | OfferResponse.to_dict() 测试 |
| TestUserAgentV4Integration | 3 | v4 集成测试 |

### 覆盖的验收标准

- [x] **AC-1**: UserAgent 收到 `demand_offer` 后能生成响应
- [x] **AC-2**: 响应包含 `response_type` 字段（"offer" 或 "negotiate"）
- [x] **AC-3**: negotiate 类型时，`negotiation_points` 非空
- [x] **AC-4**: 响应包含 `message_id` 字段（用于幂等）
- [x] **AC-5**: LLM 失败时，返回降级响应（默认 participate）
- [x] **AC-6**: SSE 事件 `towow.offer.submitted` 被正确发布
- [x] **AC-7**: SSE 事件包含 `negotiation_summary`（如有）
