# STORY-04: 方案聚合

> **文档路径**: `.ai/epic-multiagent-negotiation/STORY-04-proposal-aggregation.md`
>
> * EPIC_ID: E-001
> * STORY_ID: STORY-04
> * 优先级: P0
> * 状态: 可开发
> * 创建日期: 2026-01-22

---

## 用户故事

**作为** Channel 管理员 Agent
**我希望**将所有收到的 Offer 整合成一个结构化的协作方案
**以便**需求发起者和参与者都能清晰看到"谁做什么"的分工安排

---

## 背景与动机

### 核心原则（价值排序）

1. **用户利益优先**：方案要最大程度满足发起需求的用户
2. **参与者都能接受**：方案要让每个被选中的人都觉得合理
3. **高效**：减少不必要的来回协商

### 方案聚合的核心任务

**不是**：简单地把所有回应拼在一起
**而是**：理解每个人能贡献什么，设计一个让大家都能发挥价值的方案

### 需要思考的问题

1. 需求的核心是什么？哪些是必须满足的？
2. 每个回应者能贡献什么？
3. 谁是必需的？谁是锦上添花？
4. 如何分配任务，让大家都能接受？
5. 有没有冲突需要协调？

---

## 验收标准

### AC-1: 方案满足需求核心目标
**Given** 需求是 "办一场50人的AI聚会"
**When** 收集到场地、嘉宾、策划的 Offer
**Then** 方案必须包含这些核心角色的分工

### AC-2: 每个角色有明确职责
**Given** 方案中有多个参与者
**When** 查看方案 assignments
**Then** 每个参与者都有：
- 明确的角色定位
- 具体的职责描述
- 依赖关系（如果有）

### AC-3: 有选择理由说明
**Given** 收到 10 个 Offer，最终选择 5 个
**When** 生成方案
**Then** 方案包含 `rationale` 字段，解释为什么选择这些人

### AC-4: 处理冲突和重叠
**Given** 两个 Agent 都想做同一个角色
**When** 生成方案
**Then** 方案要么选择一个，要么分工协作，并说明理由

### AC-5: 妥协方案生成（无完美匹配时）
**Given** 收到的 Offer 无法完全满足需求（如缺少关键角色）
**When** 生成方案
**Then** 生成妥协方案，说明：
- 目前能做到什么
- 还缺什么
- 建议如何解决

---

## 技术要点

### LLM 调用
- **提示词**: 提示词 4 - 方案聚合、提示词 9 - 妥协方案生成
- **调用位置**: `openagents/agents/channel_admin.py`
- **模型**: Claude API

### 依赖模块
- `services/llm.py`: LLM 调用封装
- `openagents/agents/channel_admin.py`: Channel 管理员 Agent
- STORY-03 的响应收集结果

### 接口定义

**输入**:
```python
class AggregationRequest(BaseModel):
    demand: DemandUnderstanding           # 已理解的需求
    offers: list[AgentResponse]           # 所有收到的响应
    channel_id: str                       # 协商 Channel ID
```

**输出**:
```python
class Proposal(BaseModel):
    proposal_id: str
    demand_id: str
    version: int = 1
    summary: str                          # 方案概述
    objective: str                        # 方案目标
    assignments: list[Assignment]         # 角色分配
    timeline: Timeline                    # 时间线
    rationale: str                        # 选择理由
    gaps: list[str] = []                  # 识别到的缺口
    confidence: str                       # "high" | "medium" | "low"
    created_at: datetime

class Assignment(BaseModel):
    agent_id: str
    display_name: str
    role: str                             # 角色名称
    responsibility: str                   # 具体职责
    dependencies: list[str] = []          # 依赖的其他角色/条件
    notes: str = ""                       # 备注

class Timeline(BaseModel):
    start_date: str
    milestones: list[Milestone]

class Milestone(BaseModel):
    name: str
    date: str
```

### 提示词模板

```
你是这个协商Channel的管理员。

原始需求：
{demand_description}

需求上下文：
{demand_context}

收到的回应：
---
{all_responses}
---

请设计一个初步方案。

思考：
1. 这个需求的核心是什么？必须满足什么？
2. 每个人能贡献什么？
3. 谁是必需的，谁是加分项？
4. 如何分配任务？
5. 有没有冲突需要协调？

原则：
- 用户利益优先：方案要最大程度满足需求
- 参与者都能接受：每个人的任务要合理
- 高效：减少不必要的协商

输出 JSON 格式：
{
  "summary": "方案概述",
  "objective": "方案目标",
  "assignments": [
    {
      "agent_id": "xxx",
      "display_name": "xxx",
      "role": "角色名称",
      "responsibility": "具体职责",
      "dependencies": ["依赖..."],
      "notes": "备注"
    }
  ],
  "timeline": {
    "start_date": "待定",
    "milestones": [
      {"name": "方案确认", "date": "本周内"}
    ]
  },
  "rationale": "为什么选择这些人",
  "gaps": ["如果有缺口..."],
  "confidence": "high|medium|low"
}
```

---

## 测试场景

| 场景 | 输入 | 预期输出 |
|------|------|----------|
| 正常场景：完美匹配 | 需求：50人聚会；Offer：场地+嘉宾+策划 | 完整方案，confidence: "high" |
| 部分匹配 | 需求：50人聚会；Offer：只有场地和嘉宾 | 方案+gaps: ["缺少活动策划"]，confidence: "medium" |
| 角色冲突 | 两人都想当主讲嘉宾 | 选择一人或分配不同话题，说明选择理由 |
| 妥协场景 | 需求：北京场地；Offer：只有上海场地 | 妥协方案：说明可行的替代方案 |
| 无有效响应 | 所有人都 decline | 生成"无法组建团队"的说明和建议 |

---

## Proposal 结构详解

### 完整示例

```json
{
  "proposal_id": "prop_001",
  "demand_id": "d-abc12345",
  "version": 1,
  "summary": "关于'北京AI主题聚会'的协作方案",
  "objective": "在北京组织一次50人规模的高质量AI技术交流活动",
  "assignments": [
    {
      "agent_id": "agent_bob",
      "display_name": "Bob",
      "role": "场地提供者",
      "responsibility": "提供朝阳区咖啡厅场地（容纳50人），负责茶歇和投影设备",
      "dependencies": [],
      "notes": "场地费可商量，周末下午2-6点最佳"
    },
    {
      "agent_id": "agent_alice",
      "display_name": "Alice",
      "role": "主讲嘉宾",
      "responsibility": "45分钟AI技术分享，含demo演示",
      "dependencies": ["需要Bob确认场地时间"],
      "notes": "可准备Q&A环节"
    },
    {
      "agent_id": "agent_charlie",
      "display_name": "Charlie",
      "role": "活动策划/主持",
      "responsibility": "设计活动流程，现场主持和协调",
      "dependencies": [],
      "notes": "有5年活动策划经验"
    }
  ],
  "timeline": {
    "start_date": "2026-02-15",
    "milestones": [
      {"name": "方案确认", "date": "本周内"},
      {"name": "场地踩点", "date": "下周"},
      {"name": "活动执行", "date": "2026-02-15"}
    ]
  },
  "rationale": "选择Bob是因为他的场地位置好且容量匹配；Alice是AI领域专家且有分享经验；Charlie虽然是条件参与，但他的策划经验对活动成功很重要。David和Emma因为时间冲突未能参与。",
  "gaps": [],
  "confidence": "high"
}
```

### 妥协方案示例

```json
{
  "proposal_id": "prop_002",
  "demand_id": "d-abc12345",
  "version": 1,
  "summary": "关于'北京AI主题聚会'的妥协方案",
  "objective": "尽可能满足活动需求，但存在一些限制",
  "assignments": [
    {
      "agent_id": "agent_bob",
      "display_name": "Bob",
      "role": "场地提供者",
      "responsibility": "提供场地（但只能容纳30人）",
      "dependencies": [],
      "notes": "建议控制参与人数或寻找更大场地"
    }
  ],
  "timeline": {
    "start_date": "待定",
    "milestones": []
  },
  "rationale": "目前只找到场地资源，缺少嘉宾和策划。Bob的场地虽然只能容纳30人，但可以先用这个方案，同时继续寻找更大的场地。",
  "gaps": ["缺少AI领域分享嘉宾", "缺少活动策划", "场地容量不足（30人 vs 需求50人）"],
  "confidence": "low",
  "suggestions": [
    "可以尝试联系更多AI领域的朋友",
    "考虑缩小活动规模到30人",
    "可以尝试在其他平台发布嘉宾招募"
  ]
}
```

---

## UI 证据要求

- [ ] 方案卡片截图（显示角色分配和职责）
- [ ] 多个方案版本对比（如果有迭代）
- [ ] 妥协方案的特殊展示（显示缺口和建议）
- [ ] 方案时间线展示

---

## OPEN 事项

| 编号 | 问题 | 状态 |
|------|------|------|
| OPEN-4.1 | 如何处理多个版本的方案（协商迭代后） | 待确认：保留历史版本，显示最新版本 |
| OPEN-4.2 | 妥协方案的自动建议是否需要调用子网 | 待确认：MVP 先只给文字建议，不自动触发子网 |

---

## 关联文档

- PRD: `./PRD-multiagent-negotiation-v3.md` (F4 章节)
- 提示词: `/docs/提示词清单.md` (提示词 4, 9)
- 技术方案: `/docs/tech/TECH-TOWOW-MVP-v1.md` (4.3 章节)
- 依赖 Story: `./STORY-03-response-collection.md`
