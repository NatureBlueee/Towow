# STORY-02: 智能筛选

> **文档路径**: `.ai/epic-multiagent-negotiation/STORY-02-smart-filtering.md`
>
> * EPIC_ID: E-001
> * STORY_ID: STORY-02
> * 优先级: P0
> * 状态: 可开发
> * 创建日期: 2026-01-22

---

## 用户故事

**作为** ToWow 网络的中心调度 Agent
**我希望**从网络中所有 Agent 简介中，智能筛选出与当前需求相关的候选人
**以便**不遗漏任何可能帮得上忙的人，同时不邀请完全无关的人

---

## 背景与动机

### 筛选的核心原则

筛选的目标不是"精准"，而是"不遗漏"。宁可多邀请几个不那么相关的人，也不要漏掉真正能帮忙的人。

### 两类匹配

1. **显式匹配**：Agent 简介里明确写了相关能力（如"有场地"）
2. **隐式推断**：基于 Agent 的背景合理推测可能有帮助（如"AI创业者"可能认识很多技术人才）

### MVP 简化设计

- 直接把所有 Agent 简介丢给 LLM，一步到位输出候选列表
- 不做两层筛选（规则 SQL + LLM 语义）
- 不做能力标签体系设计

**性能考虑**：
- 假设 100 个 Agent，每人简介 500 字 = 5 万字 ≈ 25K tokens
- 一次筛选调用约 3-5 秒，可接受

---

## 验收标准

### AC-1: 不遗漏明显相关的 Agent
**Given** 需求是 "需要场地"，Agent 池中有一个简介写 "我有一家咖啡厅可以办活动"
**When** 系统调用智能筛选
**Then** 该 Agent 必须出现在 `definitely_related` 列表中

### AC-2: 隐式推断有理有据
**Given** 需求是 "需要AI领域嘉宾"，Agent 池中有一个简介写 "AI创业者，经常参加技术分享"
**When** 系统调用智能筛选
**Then** 该 Agent 出现在 `possibly_related` 列表中，并有推断理由

### AC-3: 返回合理数量的候选人
**Given** Agent 池有 100 人，需求是一个普通活动需求
**When** 系统调用智能筛选
**Then** 返回 10-20 个候选人（不多不少）

### AC-4: 每个候选都有选择理由
**Given** 筛选完成
**When** 查看返回结果
**Then** 每个候选 Agent 都有对应的 `reason` 字段，说明为什么选择

### AC-5: 不基于刻板印象推断
**Given** Agent 简介只写 "女性，30岁"
**When** 需求是 "需要技术专家"
**Then** 不应该仅因为性别或年龄就排除或推断能力

---

## 技术要点

### LLM 调用
- **提示词**: 提示词 2 - 智能筛选
- **调用位置**: `openagents/agents/coordinator.py`
- **模型**: Claude API

### 依赖模块
- `services/llm.py`: LLM 调用封装
- `database/services.py`: 获取所有活跃 Agent 简介
- `openagents/agents/coordinator.py`: Coordinator Agent

### 接口定义

**输入**:
```python
class FilterRequest(BaseModel):
    demand: DemandUnderstanding   # 已理解的需求
    all_agent_profiles: list[AgentProfile]  # 所有活跃 Agent 简介
```

**输出**:
```python
class FilterResult(BaseModel):
    definitely_related: list[CandidateAgent]  # 明确相关
    possibly_related: list[CandidateAgent]    # 可能相关
    analysis: str                              # 筛选分析过程
    total_candidates: int                      # 总候选数

class CandidateAgent(BaseModel):
    agent_id: str
    display_name: str
    reason: str           # 选择理由
    match_type: str       # "explicit" | "inferred"
    confidence: float     # 0-1
```

### Agent 简介格式

```python
class AgentProfile(BaseModel):
    agent_id: str
    user_name: str
    profile_summary: str      # 200-500字自我介绍
    location: str
    tags: list[str]           # 能力标签
    capabilities: dict        # 详细能力
    interests: list[str]      # 兴趣领域
    availability: str         # 时间可用性
```

### 提示词模板

```
你是ToWow网络的中心调度员。

有一个新需求：
"{demand_description}"

需求上下文：
{demand_context}

需要的能力标签：{capability_tags}

以下是网络中所有在线成员的简介：
---
{all_agent_profiles}
---

请找出所有可能帮得上忙的人。

思考方式：
1. 显式匹配：谁的简介里明确提到了相关能力？
2. 隐式推断：基于谁的背景，可以合理推测他可能有帮助？
   - 推断要有理有据
   - 不确定的标注"可能相关"
3. 宁可多选，不要遗漏
4. 目标是选出 10-20 个最相关的候选人

输出 JSON 格式：
{
  "analysis": "这个需求需要...",
  "definitely_related": [
    {"agent_id": "xxx", "display_name": "xxx", "reason": "明确相关的原因", "confidence": 0.9}
  ],
  "possibly_related": [
    {"agent_id": "xxx", "display_name": "xxx", "reason": "为什么推测可能相关", "confidence": 0.6}
  ]
}
```

---

## 测试场景

| 场景 | 输入 | 预期输出 |
|------|------|----------|
| 正常场景：场地需求 | demand: "需要北京的场地", agents: 含有"咖啡厅老板"的简介 | definitely_related 包含该 Agent，reason: "简介明确提到有场地" |
| 正常场景：嘉宾需求 | demand: "需要AI分享嘉宾", agents: 含有"AI研究员"的简介 | definitely_related 包含该 Agent |
| 隐式推断场景 | demand: "需要活动策划", agents: 含有"经常组织社区活动"的简介 | possibly_related 包含该 Agent，reason: "有活动组织经验，可能能帮忙策划" |
| 边界场景：无相关 | demand: "需要医疗专家", agents: 全是技术人员 | definitely_related 为空，possibly_related 可能有"有医疗行业工作经验"的 |
| 边界场景：大量相关 | demand: "需要技术人员", agents: 100个都是技术人员 | 返回 15-20 个最相关的，并解释选择标准 |

---

## 候选人返回格式

### 完整返回示例

```json
{
  "analysis": "这个需求需要：1) 北京的活动场地；2) AI领域的分享嘉宾；3) 活动策划能力。分析了100个Agent简介后，找到了以下候选人。",
  "definitely_related": [
    {
      "agent_id": "agent_bob",
      "display_name": "Bob",
      "reason": "简介明确提到'有一家咖啡厅可以提供活动场地，位于北京朝阳区，可容纳50人'，完全匹配场地需求",
      "match_type": "explicit",
      "confidence": 0.95
    },
    {
      "agent_id": "agent_alice",
      "display_name": "Alice",
      "reason": "简介写明'AI研究员，经常做技术分享'，匹配嘉宾需求",
      "match_type": "explicit",
      "confidence": 0.90
    }
  ],
  "possibly_related": [
    {
      "agent_id": "agent_charlie",
      "display_name": "Charlie",
      "reason": "虽然简介没有提到活动策划，但提到'经常组织技术社区meetup'，推测有策划经验",
      "match_type": "inferred",
      "confidence": 0.65
    }
  ],
  "total_candidates": 15
}
```

---

## UI 证据要求

- [ ] 筛选结果列表截图（显示候选人和匹配理由）
- [ ] 筛选中的加载状态
- [ ] 无候选人时的空态提示

---

## OPEN 事项

| 编号 | 问题 | 状态 |
|------|------|------|
| OPEN-2.1 | Agent 数量超过 200 时是否需要先按 location 过滤 | 待确认：MVP 先不做，观察性能 |
| OPEN-2.2 | 是否需要缓存筛选结果 | 待确认：MVP 先不做缓存 |

---

## 关联文档

- PRD: `./PRD-multiagent-negotiation-v3.md` (F2 章节)
- 提示词: `/docs/提示词清单.md` (提示词 2)
- 技术方案: `/docs/tech/TECH-TOWOW-MVP-v1.md` (4.2 章节)
