# STORY-05: 多轮协商

> **文档路径**: `.ai/epic-multiagent-negotiation/STORY-05-multi-round-negotiation.md`
>
> * EPIC_ID: E-001
> * STORY_ID: STORY-05
> * 优先级: P0
> * 状态: 可开发
> * 创建日期: 2026-01-22

---

## 用户故事

**作为**收到方案的参与者 Agent
**我希望**对方案提出反馈（接受/协商/退出），并看到方案根据反馈进行调整
**以便**最终达成一个所有参与者都能接受的协作方案

---

## 背景与动机

### 为什么需要多轮协商

真实的协作不是"一锤子买卖"。参与者可能：
- 对分配的角色有不同想法
- 对时间安排有冲突
- 对职责范围有异议
- 发现新的问题需要讨论

### MVP 简化：最多 3 轮

原设计是最多 5 轮，MVP 简化为最多 3 轮，原因：
- 减少延迟，提升演示效果
- 3 轮已足够展示协商能力
- 超过 3 轮大概率是需求本身有问题

### 选择性分发

方案只分发给被选中的 Agent，未被选中的 Agent 不会收到方案通知。
- 避免无关 Agent 看到不需要他们的方案
- 只让真正参与协作的 Agent 进行后续讨论
- 未被选中的 Agent 自然知道"我这次没被需要"

---

## 验收标准

### AC-1: 反馈类型正确处理
**Given** Agent 收到方案
**When** Agent 提交反馈
**Then** 支持三种反馈类型：
- `accept`: 接受方案
- `negotiate`: 提出调整请求
- `withdraw`: 退出协商

### AC-2: 协商调整有效
**Given** Agent 提出 negotiate 反馈 "希望分享时间从30分钟改为45分钟"
**When** Channel 管理员处理反馈
**Then** 新版方案中该 Agent 的分享时间更新为 45 分钟（或给出不能调整的理由）

### AC-3: 3 轮内收敛
**Given** 开始协商
**When** 进行多轮反馈和调整
**Then** 最多 3 轮后：
- 全员 accept → 协商成功
- 仍有 negotiate → 生成当前最佳方案，标记未完全达成共识
- 核心参与者 withdraw → 协商失败或重新筛选

### AC-4: Agent 退出处理
**Given** 某个 Agent 选择 withdraw
**When** 处理退出
**Then**
- 如果是非核心角色：继续协商，方案移除该 Agent
- 如果是核心角色：尝试从 possibly_related 中补充，或标记协商失败

### AC-5: 协商终止条件明确
**Given** 协商进行中
**When** 满足以下任一条件
**Then** 协商终止：
- 所有被选中的 Agent 都 accept
- 已进行 3 轮
- 核心 Agent 退出且无法替补

---

## 技术要点

### LLM 调用
- **提示词**: 提示词 5 - 方案反馈、提示词 6 - 方案调整
- **调用位置**:
  - 反馈生成：`openagents/agents/user_agent.py`
  - 方案调整：`openagents/agents/channel_admin.py`
- **模型**: Claude API

### 依赖模块
- `services/llm.py`: LLM 调用封装
- `openagents/agents/user_agent.py`: 生成反馈
- `openagents/agents/channel_admin.py`: 处理反馈、调整方案
- STORY-04 的方案聚合结果

### 接口定义

**反馈输入**:
```python
class FeedbackRequest(BaseModel):
    agent_profile: AgentProfile
    proposal: Proposal
    assignment: Assignment      # 该 Agent 在方案中的分配
```

**反馈输出**:
```python
class ProposalFeedback(BaseModel):
    agent_id: str
    display_name: str
    feedback_type: str          # "accept" | "negotiate" | "withdraw"
    reasoning: str              # 反馈理由
    proposed_changes: dict = {} # negotiate 时的调整建议
    round: int
    submitted_at: datetime
```

**方案调整输入**:
```python
class AdjustmentRequest(BaseModel):
    demand: DemandUnderstanding
    current_proposal: Proposal
    feedbacks: list[ProposalFeedback]
    round: int
```

**方案调整输出**:
```python
class AdjustedProposal(BaseModel):
    proposal: Proposal          # 更新后的方案（version + 1）
    changes_made: list[str]     # 做了哪些调整
    changes_rejected: list[str] # 拒绝了哪些调整请求（附理由）
    should_continue: bool       # 是否需要继续协商
```

### 反馈提示词模板

```
你是{用户名}的数字分身。

关于"{demand_description}"这个需求，管理员给你分配的任务是：

角色：{role}
具体任务：{specific_task}
备注：{notes}

作为{用户名}，你对这个安排有什么想法？

选项：
1. accept：这个安排我可以
2. negotiate：基本可以，但我想调整...（请说明想调整什么，为什么）
3. withdraw：这次我参与不了（请简单说明原因）

请真实表达你的想法。

输出 JSON 格式：
{
  "feedback_type": "accept|negotiate|withdraw",
  "reasoning": "我的考虑是...",
  "proposed_changes": {
    "field": "new_value",
    "reason": "为什么想改"
  }
}
```

### 方案调整提示词模板

```
你是这个协商Channel的管理员。

当前方案（版本 {version}）：
{current_plan}

收到的反馈：
---
{all_feedback}
---

请调整方案。

原则：
1. 用户利益优先：不能损害需求方的核心利益
2. 参与者都能接受：调整要让大家都能通过
3. 高效：判断是否还需要继续协商

思考：
- 每个调整要求是否合理？
- 能否满足？会影响谁？
- 如何平衡？

输出 JSON：
{
  "proposal": {...},  // 更新后的方案
  "changes_made": ["调整了xxx", "调整了yyy"],
  "changes_rejected": [
    {"request": "xxx", "reason": "不能调整的原因"}
  ],
  "should_continue": true|false
}
```

---

## 测试场景

| 场景 | 输入 | 预期输出 |
|------|------|----------|
| 全员接受（第1轮） | 所有人 feedback: accept | 协商成功，进入最终确认 |
| 部分协商（第1轮） | 2人 accept，1人 negotiate | 调整方案，进入第2轮 |
| 3轮后仍有分歧 | 连续3轮都有 negotiate | 生成当前最佳方案，标记"部分共识" |
| 核心角色退出 | 唯一场地提供者 withdraw | 尝试从 possibly_related 补充，或标记失败 |
| 非核心角色退出 | 锦上添花的角色 withdraw | 继续协商，方案移除该角色 |

---

## 反馈类型详细说明

### Accept（接受）

```json
{
  "agent_id": "agent_bob",
  "display_name": "Bob",
  "feedback_type": "accept",
  "reasoning": "方案合理，角色分配符合我的能力，时间也没问题",
  "proposed_changes": {},
  "round": 1
}
```

### Negotiate（协商）

```json
{
  "agent_id": "agent_alice",
  "display_name": "Alice",
  "feedback_type": "negotiate",
  "reasoning": "整体可以，但分享时间太短了",
  "proposed_changes": {
    "responsibility": "45分钟AI技术分享（原30分钟）",
    "reason": "30分钟太紧凑，案例比较复杂需要demo演示，希望能有充分时间讲解"
  },
  "round": 1
}
```

### Withdraw（退出）

```json
{
  "agent_id": "agent_charlie",
  "display_name": "Charlie",
  "feedback_type": "withdraw",
  "reasoning": "非常抱歉，公司那边突然有个紧急项目，需要我全力投入。真的很对不起大家，下次一定参加。",
  "proposed_changes": {},
  "round": 1
}
```

---

## 轮次控制逻辑

```
Round 1:
├── 分发方案 v1
├── 收集反馈
├── 判断：
│   ├── 全员 accept → 协商成功，进入缺口识别
│   ├── 有 negotiate → 调整方案，进入 Round 2
│   └── 核心 withdraw → 尝试替补或失败

Round 2:
├── 分发方案 v2
├── 收集反馈
├── 判断：（同上）

Round 3:
├── 分发方案 v3
├── 收集反馈
├── 判断：
│   ├── 全员 accept → 协商成功
│   └── 仍有分歧 → 生成"当前最佳方案"，标记部分共识
```

### 终止条件决策树

```
if all(feedback == "accept"):
    status = "success"
    → 进入缺口识别

elif round >= 3:
    if majority_accept:
        status = "partial_consensus"
        → 生成当前最佳方案
    else:
        status = "negotiation_timeout"
        → 生成妥协方案

elif core_agent_withdraw:
    if replacement_available:
        → 邀请替补，重新协商
    else:
        status = "failed"
        → 通知需求无法满足

else:
    → 调整方案，进入下一轮
```

---

## UI 证据要求

- [ ] 方案反馈界面截图（显示三种反馈选项）
- [ ] 协商时间线（显示多轮迭代）
- [ ] Agent 退出的提示展示
- [ ] 3轮后的结果展示（成功/部分共识/失败）

---

## OPEN 事项

| 编号 | 问题 | 状态 |
|------|------|------|
| OPEN-5.1 | 超时未反馈的 Agent 如何处理 | 待确认：30秒超时视为 accept（默认接受） |
| OPEN-5.2 | 部分共识的方案是否可以直接执行 | 待确认：MVP 先允许，但标记风险 |

---

## 关联文档

- PRD: `./PRD-multiagent-negotiation-v3.md` (F5 章节)
- 提示词: `/docs/提示词清单.md` (提示词 5, 6)
- 技术方案: `/docs/tech/TECH-TOWOW-MVP-v1.md` (4.3 章节)
- 依赖 Story: `./STORY-04-proposal-aggregation.md`
