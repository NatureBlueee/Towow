# Issue 005: App Store 协商图谱布局失效 + 方案显示丢失

**日期**: 2026-02-12
**严重度**: 高（用户可见，核心展示功能不可用）
**影响范围**: App Store 页面 (`/store/`, `/store/[scene]`)

## 症状

1. **图谱节点全部重叠**：15 个 Agent 在图谱中挤成一坨，看起来只有 1 个可见
2. **Task 节点重叠**：底部任务节点互相叠加，无法分辨
3. **方案不显示**：协商完成后（状态"已完成"），没有方案展示区域
4. **反复修不好**：多次迭代未解决，说明不是参数问题而是结构问题

## 根因分析

### 根因 1：SVG 布局空间数学不可能

**文件**: `website/components/negotiation/graph/layout.ts`, `types.ts`

固定 800×600 SVG viewBox，Agent 圆半径 r=30（直径 60px），水平排列区间 540px（x: 130→670）。

| Agent 数量 | 间距 (px) | 直径 (px) | 结果 |
|-----------|-----------|-----------|------|
| 5 | 135 | 60 | 正常 |
| 8 | 77 | 60 | 勉强 |
| 10 | 60 | 60 | 刚好相切 |
| 15 | 38.6 | 60 | **重叠 21px/对** |
| 20 | 28.4 | 60 | **重叠 32px/对** |

SVG 后绘制的元素覆盖先绘制的，导致只有最后一个 Agent 可见。

Task 节点同理：r=16（直径 32px），460px 区间，超过 15 个就开始重叠。

**结论**：这不是 bug，是**设计容量限制**。固定坐标 + 固定半径 + 单行排列 = 超过 10 个节点必然失效。

### 根因 2：PlanOutput 显示条件不完整

**文件**: `website/app/store/page.tsx:108`

```tsx
// 主页 — 只检查 planOutput（来自 GET 轮询）
{negotiation.planOutput && (
  <PlanOutput ... />
)}
```

```tsx
// 场景页 — 条件更宽（也检查 planJson 和 completed）
{(negotiation.planOutput || negotiation.planJson || negotiation.phase === 'completed') && (
  <PlanOutput ... />
)}
```

**问题链**：
1. WS `plan.ready` 事件到达 → phase 立即变为 `completed` → 用户看到"已完成"
2. `planJson` 从 WS 事件中提取，立即可用
3. `planOutput` 来自 GET 轮询（2s 间隔），还没有值
4. 即使轮询到了，`plan_output` 如果是空字符串 `""` 也是 falsy
5. **结果**：用户看到"已完成"但看不到方案

### 元问题：为什么反复修不好

1. **目标偏移**：之前的改动集中在 `/negotiation` 页面的组件，但用户看的是 App Store 页面
2. **设计容量问题被当成实现 bug**：调坐标、改半径都只是缓解，不解决根本
3. **复杂度过高**：Store 事件 → adapter → NegotiationState → computeLayout → SVG → 6 个子组件 → 各自的 CSS modules。任何一层出问题都难以定位
4. **共享组件的副作用**：NegotiationGraph 被 `/negotiation` 和 `/store/` 共用，改一个怕影响另一个，结果谁都改不好

## 数据流追踪

```
后端 V1 Engine
  ↓ resonance.activated (agents: 15个, filtered_agents: 0个)
  ↓ WS event → useStoreWebSocket → events[]
  ↓
store-negotiation-adapter.ts: buildNegotiationState()
  ↓ resonanceAgents: 15个 (全部来自 data.agents)
  ↓ filteredAgents: 0个
  ↓
layout.ts: computeLayout()
  ↓ 15个 AgentNode at y=285, x spread 130→670 (间距 38.6px)
  ↓
NegotiationGraph.tsx: SVG 渲染
  ↓ 15个 AgentNode 组件，直径 60px，互相重叠
  ↓ 只有最后绘制的可见

方案显示:
  plan.ready WS 事件 → planJson 立即可用 (hook line 211-213)
  GET 轮询 → plan_output 延迟到达 (hook line 338)
  store/page.tsx:108 只检查 planOutput → 不渲染 PlanOutput
```

## 涉及文件

| 文件 | 角色 | 问题 |
|------|------|------|
| `website/app/store/page.tsx` | 主页 | PlanOutput 条件不完整 |
| `website/components/store/NegotiationProgress.tsx` | 图谱容器 | 直接使用 NegotiationGraph（SVG） |
| `website/components/negotiation/graph/layout.ts` | 布局算法 | 固定坐标，不支持 >10 节点 |
| `website/components/negotiation/graph/types.ts` | 布局常量 | 800×600, r=30 |
| `website/components/negotiation/graph/NegotiationGraph.tsx` | SVG 容器 | animation queue 等复杂度 |
| `website/components/negotiation/graph/AgentNode.tsx` | Agent 节点 | r=30 不可缩放 |
| `website/lib/store-negotiation-adapter.ts` | 适配器 | 数据转换层（本身无问题） |

## 修复方向

### 快速修复（方案显示）
- `store/page.tsx` 的 PlanOutput 条件对齐场景页

### 结构修复（图谱布局）
需要本质层面的重新思考——不是"怎么在 800×600 SVG 里塞更多节点"，而是"协商过程的可视化本质是什么"。

详见后续 ADR。
