# STORY-06: 缺口识别与子网（简化版）

> **文档路径**: `.ai/epic-multiagent-negotiation/STORY-06-gap-subnet.md`
>
> * EPIC_ID: E-001
> * STORY_ID: STORY-06
> * 优先级: P1
> * 状态: 可开发
> * 创建日期: 2026-01-22

---

## 用户故事

**作为** Channel 管理员 Agent
**我希望**在方案确认后，识别是否有遗漏的能力缺口，并决定是否触发子网递归
**以便**尽可能完整地满足用户需求，展示 ToWow 的"递归协作"能力

---

## 背景与动机

### 为什么需要缺口识别

即使收到了多个 Offer 并聚合成方案，也可能存在：
- 需求中提到但没人能提供的能力
- 方案执行过程中隐含需要但未明确的资源
- 参与者反馈中提到的依赖项

### MVP 简化：最多 1 层递归

原设计是最多 2 层递归，MVP 简化为最多 1 层，原因：
- 降低复杂度，减少开发时间
- 1 层递归已足够展示"递归协作"能力
- 更深的递归可能导致延迟过长

### 子网递归的核心价值

子网递归是 ToWow "最小完备性"的体现：
- 同一个协作机制可以无限扩展
- 展示"道生一，一生二"的理念
- 复杂需求自动分解为子需求

---

## 验收标准

### AC-1: 识别明显缺口
**Given** 需求是 "办聚会，需要场地、嘉宾、摄影"，方案只有场地和嘉宾
**When** 调用缺口识别
**Then** 识别出 gaps: ["摄影师"]

### AC-2: 评估缺口重要性
**Given** 识别出多个缺口
**When** 输出缺口列表
**Then** 每个缺口都有 importance 分数（0-100）和理由

### AC-3: 递归判断有依据
**Given** 识别出缺口
**When** 判断是否递归
**Then** 基于三重条件做出判断：
- 条件1：递归能显著提升需求满足度
- 条件2：利益相关方认为递归有价值
- 条件3：成本效益比合理

### AC-4: 子网能独立协商
**Given** 决定触发子网递归
**When** 创建子需求
**Then** 子需求能独立完成整个协商流程（筛选→响应→聚合→协商）

### AC-5: 子网结果回传
**Given** 子网协商完成
**When** 返回结果给父网
**Then** 父方案更新，包含子网找到的资源

---

## 技术要点

### LLM 调用
- **提示词**: 提示词 7 - 缺口识别、提示词 8 - 递归判断
- **调用位置**: `openagents/agents/channel_admin.py`, `services/subnet_manager.py`
- **模型**: Claude API

### 依赖模块
- `services/llm.py`: LLM 调用封装
- `services/gap_identification.py`: 缺口识别服务
- `services/subnet_manager.py`: 子网管理
- `openagents/agents/channel_admin.py`: Channel 管理员

### 接口定义

**缺口识别输入**:
```python
class GapIdentificationRequest(BaseModel):
    demand: DemandUnderstanding
    final_proposal: Proposal
    agent_feedbacks: list[ProposalFeedback]
```

**缺口识别输出**:
```python
class GapIdentificationResult(BaseModel):
    is_complete: bool
    gaps: list[Gap]
    analysis: str

class Gap(BaseModel):
    gap_type: str               # 缺口类型，如 "摄影师"
    importance: int             # 重要性 0-100
    reason: str                 # 为什么重要
    suggested_capability_tags: list[str]  # 建议的能力标签
```

**递归判断输入**:
```python
class RecursionDecisionRequest(BaseModel):
    demand: DemandUnderstanding
    gaps: list[Gap]
    current_proposal: Proposal
    agent_feedbacks: list[ProposalFeedback]
    estimated_cost: dict        # 预估成本（tokens, 时间）
```

**递归判断输出**:
```python
class RecursionDecision(BaseModel):
    should_recurse: bool
    condition_1_met: bool       # 满足度提升
    condition_1_analysis: str
    condition_2_met: bool       # 利益相关方支持
    condition_2_analysis: str
    condition_3_met: bool       # 成本效益比
    condition_3_analysis: str
    sub_demands: list[SubDemand] = []

class SubDemand(BaseModel):
    description: str
    capability_tags: list[str]
    priority: str               # "high" | "medium" | "low"
    parent_demand_id: str
    depth: int = 1              # MVP 固定为 1
```

### 缺口识别提示词模板

```
原始需求是：{demand_description}

当前方案是：
{final_plan}

请检查：
1. 这个方案是否完整满足了需求？
2. 有没有遗漏的方面？
3. 如果有缺口，重要性如何？

输出 JSON：
{
  "is_complete": true|false,
  "analysis": "分析过程...",
  "gaps": [
    {
      "gap_type": "摄影师",
      "importance": 70,
      "reason": "需要记录活动内容，用于后续传播",
      "suggested_capability_tags": ["摄影", "活动拍摄"]
    }
  ]
}
```

### 递归判断提示词模板

```
原始需求：{demand_description}
当前方案：{aggregated_plan}
Agents反馈：{agent_responses}
识别的缺口：{gaps}

请判断触发递归是否满足以下三个条件：

条件1：能更好满足原始需求
- 当前需求满足度：估计多少%？
- 递归后满足度：预计多少%？
- 提升幅度是否超过15%？

条件2：能让所有利益相关方更满意
- 现有参与者对递归的态度？
- 是否有人明确表示递归会带来更多价值？

条件3：Token使用效率最大化
- 预估递归成本（创建子网、筛选、协商）
- 预估收益
- 成本效益比是否超过1.5？

输出 JSON：
{
  "should_recurse": true|false,
  "condition_1_met": true|false,
  "condition_1_analysis": "满足度分析...",
  "condition_2_met": true|false,
  "condition_2_analysis": "利益相关方分析...",
  "condition_3_met": true|false,
  "condition_3_analysis": "成本效益分析...",
  "sub_demands": [
    {
      "description": "子需求描述",
      "capability_tags": ["标签1", "标签2"],
      "priority": "high"
    }
  ]
}
```

---

## 测试场景

| 场景 | 输入 | 预期输出 |
|------|------|----------|
| 无缺口 | 方案完整满足需求 | is_complete: true, gaps: [], should_recurse: false |
| 有缺口但不值得递归 | 缺少茶歇服务（importance: 30） | is_complete: false, gaps: [茶歇], should_recurse: false |
| 有缺口且值得递归 | 缺少摄影师（importance: 70），参与者支持 | should_recurse: true, sub_demands: [摄影师需求] |
| 子网成功 | 子网找到摄影师 | 父方案更新，包含摄影师角色 |
| 子网失败 | 子网未找到摄影师 | 父方案标记缺口未解决，给出建议 |

---

## 1 层递归说明

### 递归流程

```
父 Channel（dm_001）:
├── 方案确认
├── 缺口识别 → "需要摄影师"
├── 递归判断 → 满足三重条件
├── 创建子需求
│
└── 子 Channel（dm_001_sub_1）:
    ├── 子需求广播
    ├── 智能筛选（找摄影师）
    ├── 邀请、收集Offer
    ├── 协商（最多3轮）
    └── 返回结果 → "agent_kevin提供摄影服务"
│
├── 整合子网结果
└── 更新最终方案
```

### 数据关联

```json
{
  "parent_demand_id": "dm_001",
  "parent_channel_id": "dm_001",
  "sub_demand_id": "dm_001_sub_1",
  "sub_channel_id": "dm_001_sub_1",
  "depth": 1,
  "sub_result": {
    "status": "success",
    "摄影师": {
      "provider": "agent_kevin",
      "details": "专业活动摄影，提供照片和视频"
    }
  }
}
```

### MVP 限制

- **最多 1 层递归**：depth <= 1
- **不做循环检测**：假设 1 层内不会出现循环依赖
- **子网与父网独立**：不共享参与者（同一个 Agent 可以同时在父网和子网）

---

## UI 证据要求

- [ ] 缺口识别结果展示（显示缺口列表和重要性）
- [ ] 递归决策展示（三重条件判断过程）
- [ ] 子网协商的嵌套展示
- [ ] 子网结果回传后的方案更新展示

---

## OPEN 事项

| 编号 | 问题 | 状态 |
|------|------|------|
| OPEN-6.1 | 子网超时如何处理 | 待确认：设置 60 秒超时，超时视为子网失败 |
| OPEN-6.2 | 多个缺口是否可以并行触发多个子网 | 待确认：MVP 先串行处理，一个一个来 |
| OPEN-6.3 | 子网的 Agent 池是否与父网相同 | 待确认：MVP 使用相同 Agent 池 |

---

## 关联文档

- PRD: `./PRD-multiagent-negotiation-v3.md` (F6 章节)
- 提示词: `/docs/提示词清单.md` (提示词 7, 8)
- 技术方案: `/docs/tech/TECH-TOWOW-MVP-v1.md` (supplement-04)
- 依赖 Story: `./STORY-05-multi-round-negotiation.md`
