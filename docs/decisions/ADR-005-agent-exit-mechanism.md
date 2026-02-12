# ADR-005: Agent 退出机制 — Center 主动淘汰 + 实时事件

**日期**: 2026-02-12
**状态**: 讨论中
**关联**: 架构设计 Section 4.6（筛选阶段状态检测）, ADR-004（Bloom Filter）
**优先级**: 高（比 ADR-004 更紧急）

## 背景

协商流程中，Center 在收到所有 offer 后进行多轮综合评估。在这个过程中，Center 应该能够淘汰不相关的 agent——但这个能力**完全不存在**。

### 现状诊断

| 能力 | 状态 |
|------|------|
| `AgentState.EXITED` 枚举值 | ✅ 已定义 |
| 超时/报错自动退出 | ✅ 自动（30s timeout → EXITED） |
| Center `dismiss_agents` 工具 | ❌ 不存在（Center 有 5 个工具，无 dismiss） |
| Engine 处理 dismiss 调用 | ❌ 无 handler |
| 单个 agent 退出事件 | ❌ 不存在（只有 barrier.complete 聚合 exited_count） |
| 前端知道哪个 agent 退出 | ❌ 只收到退出总数 |
| 退出动画/视觉反馈 | ❌ 无 |

### 影响

- Center 评估 offer 后即使觉得某个 agent 不相关，无法淘汰，plan 中会包含所有人
- 用户看不到"有些 agent 被筛掉"的过程，协商显得是一次性的而非逐步精炼
- 退出动画是三层筛选可视化（ADR-004）的基础设施——没有退出动画，Bloom Filter 的层层淘汰效果也做不出来

## 目标

1. Center 能在综合评估阶段主动淘汰 agent（通过 tool call）
2. 每个 agent 退出时前端实时收到事件（包含 agent_id + 退出原因）
3. 前端对退出的 agent 有视觉反馈（淡出/划线/标记）
4. 超时/报错导致的自动退出也推送同样的事件

## 选项分析

### 选项 A: Center 新增 dismiss_agents 工具

Center 的 tool schema 新增 `dismiss_agents`，Engine 在 `_run_synthesis` 中处理。

```python
# Center 调用
dismiss_agents(agent_ids=["agent_123", "agent_456"], reason="offer 与需求方向不匹配")

# Engine 处理
for aid in agent_ids:
    participant.state = AgentState.EXITED
    push_event(agent_exited(aid, reason))
```

**优势**：
- Center 驱动，符合协议设计（Center 是综合评估者）
- 退出有明确原因（可展示给用户）
- 淘汰后的 agent 不参与后续 Center 轮次（减少 token 消耗）

**劣势**：
- 需要改 Center prompt 让它知道可以淘汰人
- Center 可能过于激进地淘汰（需要 prompt 约束）

### 选项 B: Engine 自动淘汰（基于阈值）

Engine 在收到 offer 后，自动比较 offer 质量分与阈值，低于阈值的自动淘汰。

**优势**：
- 不依赖 LLM 判断
- 确定性，可预测

**劣势**：
- offer 质量分怎么算？需要额外的评分机制
- 绕过了 Center 的语义理解能力
- 不符合协议设计（Section 0.5：判断由 Center 做，不由代码硬编码）

## 决策

**选择选项 A：Center 新增 dismiss_agents 工具。**

理由：
- 符合 Section 0.5 "代码保障流程，LLM 保障判断"的原则
- Center 是协商的综合评估者，淘汰决策属于它的职责
- 退出原因来自 Center 的语义理解，可以展示给用户看

## 实现要点

### 1. 新增事件类型

```python
# events.py
EventType.AGENT_EXITED = "agent.exited"

def agent_exited(negotiation_id, agent_id, display_name, reason, source):
    """source: "center_dismiss" | "timeout" | "error" """
    return NegotiationEvent(
        event_type=EventType.AGENT_EXITED,
        negotiation_id=negotiation_id,
        data={
            "agent_id": agent_id,
            "display_name": display_name,
            "reason": reason,
            "source": source,
        },
    )
```

### 2. Center 新增 dismiss_agents 工具

```python
# center.py — 新增工具定义
TOOL_DISMISS_AGENTS = {
    "name": "dismiss_agents",
    "description": "淘汰不适合当前协商的 agent。在第一轮评估后使用。",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要淘汰的 agent_id 列表"
            },
            "reason": {
                "type": "string",
                "description": "淘汰原因（会展示给用户）"
            }
        },
        "required": ["agent_ids", "reason"]
    }
}
```

### 3. Engine 处理 dismiss 调用

在 `_run_synthesis` 的 tool_call 循环中新增 handler：

```python
elif tool_name == "dismiss_agents":
    for aid in tool_input.get("agent_ids", []):
        p = self._find_participant(session, aid)
        if p and p.state != AgentState.EXITED:
            p.state = AgentState.EXITED
            await self._push_event(session, agent_exited(
                negotiation_id=session.negotiation_id,
                agent_id=aid,
                display_name=p.display_name,
                reason=tool_input.get("reason", ""),
                source="center_dismiss",
            ))
```

### 4. 超时/报错退出也推送事件

现有的 `_generate_one_offer` 中超时/报错路径，除了设置 `state = EXITED`，也推送 `agent.exited` 事件：

```python
except asyncio.TimeoutError:
    participant.state = AgentState.EXITED
    # 新增：推送事件
    await self._push_event(session, agent_exited(..., source="timeout"))
```

### 5. 前端处理

```typescript
case 'agent.exited':
    // 更新 participant 状态
    // 触发退出动画（淡出、划线等）
    // 显示退出原因（tooltip 或 detail panel）
```

## 影响范围

| 模块 | 改动 |
|------|------|
| `towow/core/events.py` | 新增 `AGENT_EXITED` 事件类型 + 工厂函数 |
| `towow/skills/center.py` | 新增 `dismiss_agents` 工具定义 + prompt 更新 |
| `towow/core/engine.py` | `_run_synthesis` 新增 dismiss handler + 超时退出也推送事件 |
| 前端 hooks | `useNegotiationStream` 处理 `agent.exited` 事件 |
| 前端组件 | Agent 节点退出动画 |

## 与 ADR-004 (Bloom Filter) 的关系

- ADR-005 应先于 ADR-004 实现
- 退出动画的前端基础设施（节点淡出/消失效果）可被 Bloom Filter 门控复用
- Bloom Filter 的"门控淘汰"在前端看起来就是一批 agent 同时退出
