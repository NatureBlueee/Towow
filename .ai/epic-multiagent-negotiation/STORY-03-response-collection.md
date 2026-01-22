# STORY-03: 响应收集

> **文档路径**: `.ai/epic-multiagent-negotiation/STORY-03-response-collection.md`
>
> * EPIC_ID: E-001
> * STORY_ID: STORY-03
> * 优先级: P0
> * 状态: 可开发
> * 创建日期: 2026-01-22

---

## 用户故事

**作为**被邀请参与协作的 Agent
**我希望**基于我的能力、兴趣和当前状态，独立决策是否参与这个需求
**以便**只参与真正适合我的协作，并给出真实的贡献承诺

---

## 背景与动机

### 核心理念

用户的 Agent 是用户的数字分身。当它听到一个需求时，它的反应应该是自然的、人性化的。

**不是**：生成一个标准格式的 "Offer"
**而是**：作为一个人，听到这个需求后，你会说什么？

### 三种可能的关系

1. **共创者**：我也有类似的需求，我们可以一起做
2. **贡献者**：我能提供一些帮助
3. **旁观者**：这个和我没太大关系

### 三种决策类型

| 决策类型 | 说明 | 后续流程 |
|----------|------|----------|
| `participate` | 愿意参与，提交具体贡献 | 进入方案聚合 |
| `decline` | 不参与，给出理由 | 记录但不进入协商 |
| `conditional` | 有条件参与，需要满足条件 | 进入方案聚合，条件纳入考虑 |

---

## 验收标准

### AC-1: 决策基于 Agent 实际能力
**Given** Agent 简介写 "我有一家咖啡厅"，需求是 "需要场地"
**When** Agent 收到邀请并生成响应
**Then** 应该 `participate` 且贡献内容与咖啡厅场地相关

### AC-2: Participate 响应包含具体贡献
**Given** Agent 决定参与
**When** 生成响应
**Then** `contribution` 字段包含：
- 能提供什么具体资源或能力
- 时间、地点、条件等约束
- 基于 Agent 真实背景的内容

### AC-3: Decline 响应包含合理理由
**Given** Agent 决定不参与
**When** 生成响应
**Then** `decline_reason` 字段包含：
- 真实、合理的拒绝理由
- 语气友好，不是冷冰冰的拒绝
- 可能包含推荐或建议

### AC-4: Conditional 响应明确条件
**Given** Agent 有条件参与
**When** 生成响应
**Then** `conditions` 字段包含：
- 明确的条件列表
- 每个条件是可协商的
- 说明为什么需要这个条件

### AC-5: 响应自然人性化
**Given** 任何响应场景
**When** 生成响应
**Then** 响应读起来像一个真实的人在说话，不是机械填表

---

## 技术要点

### LLM 调用
- **提示词**: 提示词 3 - 回应生成
- **调用位置**: `openagents/agents/user_agent.py`
- **模型**: Claude API

### 依赖模块
- `services/llm.py`: LLM 调用封装
- `services/secondme.py` 或 `services/secondme_mock.py`: SecondMe 服务
- `openagents/agents/user_agent.py`: 用户 Agent

### 接口定义

**输入**:
```python
class ResponseGenerationRequest(BaseModel):
    agent_profile: AgentProfile      # Agent 简介
    demand: DemandUnderstanding      # 已理解的需求
    collaboration_invite: dict       # 邀请信息（含 channel_id）
```

**输出**:
```python
class AgentResponse(BaseModel):
    offer_id: str                    # 响应 ID
    agent_id: str                    # Agent ID
    display_name: str                # 显示名称
    decision: str                    # "participate" | "decline" | "conditional"
    contribution: str = ""           # 贡献描述（participate/conditional 时必填）
    conditions: list[str] = []       # 条件列表（conditional 时必填）
    reasoning: str                   # 决策理由
    decline_reason: str = ""         # 拒绝理由（decline 时必填）
    confidence: int = 50             # 决策信心 0-100
    submitted_at: datetime
```

### 提示词模板

```
你是{用户名}的数字分身。

以下是你的简介：
{agent_profile}

你收到了一个协作邀请：
需求描述："{demand_description}"
需求上下文：{demand_context}
需要的能力：{capability_tags}

作为{用户名}，请思考：

1. 这个需求和我有关系吗？
   - 我也有类似的需求？（共创者）
   - 我能帮上什么忙？（贡献者）
   - 这个和我没太大关系？（旁观者）

2. 如果我想参与，我能提供什么？
   - 具体的资源或能力
   - 我的条件（时间、地点、费用等）

3. 我的偏好是什么？
   - 什么样的合作方式我会更喜欢？
   - 我希望从中获得什么？

4. 有什么是我需要说明的？
   - 限制条件
   - 特别说明

请用第一人称回答，就像在和朋友聊天一样。

决策选项：
- participate: 我愿意参与
- decline: 这次我不太合适参与
- conditional: 我愿意参与，但需要满足一些条件

输出 JSON 格式：
{
  "decision": "participate|decline|conditional",
  "contribution": "如果参与，我能贡献...",
  "conditions": ["如果有条件..."],
  "reasoning": "我的考虑是...",
  "decline_reason": "如果不参与，原因是...",
  "confidence": 80
}
```

---

## 测试场景

| 场景 | 输入 | 预期输出 |
|------|------|----------|
| 正常参与 | Agent: "咖啡厅老板", Demand: "需要场地" | decision: "participate", contribution: "我可以提供咖啡厅场地..." |
| 正常拒绝 | Agent: "程序员", Demand: "需要场地" | decision: "decline", decline_reason: "抱歉，我没有场地资源..." |
| 有条件参与 | Agent: "设计师，最近很忙", Demand: "需要设计支持" | decision: "conditional", conditions: ["需要提前一周确认", "只能周末"] |
| 能力不匹配 | Agent: "产品经理", Demand: "需要专业摄影" | decision: "decline", decline_reason: "摄影不是我的专长..." |
| 部分匹配 | Agent: "有场地，但在上海", Demand: "需要北京场地" | decision: "decline" 或 "conditional"（条件：可以协调北京朋友的场地） |

---

## 三种决策类型详细说明

### Participate（参与）

```json
{
  "decision": "participate",
  "contribution": "我可以提供30人的会议室，还有投影设备和茶歇。位于北京朝阳区，周末和工作日晚上都可以。",
  "conditions": [],
  "reasoning": "这个活动正好是我擅长的领域，我的咖啡厅也正好适合举办这种规模的活动，很乐意参与！",
  "decline_reason": "",
  "confidence": 90
}
```

### Decline（拒绝）

```json
{
  "decision": "decline",
  "contribution": "",
  "conditions": [],
  "reasoning": "当前需求与我的能力方向不太匹配",
  "decline_reason": "感谢邀请，但这段时间实在抽不开身。下个月有个重要项目上线，每天都在加班。如果之后还有类似活动，请一定再叫上我！",
  "confidence": 85
}
```

### Conditional（有条件参与）

```json
{
  "decision": "conditional",
  "contribution": "可以负责活动流程设计和现场协调，有5年活动策划经验",
  "conditions": [
    "需要提前一周确定具体时间",
    "希望能了解其他参与者背景",
    "如果超过50人需要增加帮手"
  ],
  "reasoning": "整体感兴趣，但需要确认时间安排和活动规模",
  "decline_reason": "",
  "confidence": 70
}
```

---

## UI 证据要求

- [ ] Agent 响应卡片截图（显示决策类型、贡献内容）
- [ ] 拒绝响应的友好展示
- [ ] 有条件参与的条件列表展示

---

## OPEN 事项

| 编号 | 问题 | 状态 |
|------|------|------|
| OPEN-3.1 | 响应超时（Agent 长时间不响应）如何处理 | 待确认：设置 30 秒超时，自动视为 decline |
| OPEN-3.2 | 是否允许 Agent 修改已提交的响应 | 待确认：MVP 先不允许修改 |

---

## 关联文档

- PRD: `./PRD-multiagent-negotiation-v3.md` (F3 章节)
- 提示词: `/docs/提示词清单.md` (提示词 3)
- 技术方案: `/docs/tech/TECH-TOWOW-MVP-v1.md` (5.3 章节)
