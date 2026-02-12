# PLAN-006: App Store 复用 NegotiationGraph 完整图谱

**日期**: 2026-02-12
**关联**: Issue 006, ADR-003, Feature 004
**状态**: 已实现

## 背景

Feature 004 在 `components/negotiation/graph/` 实现了完整的协商图谱可视化（NegotiationGraph + 6 个子组件 + 动画队列），但只服务于 `/negotiation` 开发页面。App Store 仍在用自有的简化 RadialGraphView（300x300，无交互）。

用户明确：这些组件**本来就是为 App Store 做的**，应该全量复用，不删减。

## 目标

App Store 场景页的协商进度区域，替换为 Feature 004 的完整 NegotiationGraph（800x600，全交互，全动画）。

## 变更清单

### 文件 1: `website/lib/store-negotiation-adapter.ts`（新增，~100 行）

**职责**：纯函数，将 `StoreEvent[]` 转换为 `NegotiationState` 格式。

```typescript
export function buildNegotiationState(
  events: StoreEvent[],
  phase: NegotiationPhase,
): NegotiationState
```

**映射逻辑**（数据已经全在 WS 事件里）：

| 事件类型 | 提取字段 | 目标字段 |
|----------|---------|---------|
| `formulation.ready` | raw_intent, formulated_text, enrichments | `formulation` |
| `resonance.activated` | agents[], filtered_agents[] | `resonanceAgents`, `filteredAgents` |
| `offer.received` | agent_id, display_name, content, capabilities | `offers[]` |
| `barrier.complete` | — | phase 转换 |
| `center.tool_call` | tool_name, tool_args, round_number | `centerActivities[]` |
| `plan.ready` | plan_text, plan_json | `plan` |
| `sub_negotiation.started` | sub_negotiation_id, gap_description | `subNegotiations[]` |

**缺失字段处理**：
- `filtered_agents`：后端未传时给空数组（图谱正常渲染，只是没有灰色节点）
- `plan_json`：可能从 WS 事件或 REST 轮询拿到，两路取第一个非空值

### 文件 2: `website/components/store/NegotiationProgress.tsx`（修改）

**变更**：
1. 导入 `NegotiationGraph` 和 `DetailPanel`（从 `@/components/negotiation/`）
2. 导入 `buildNegotiationState`（从 `@/lib/store-negotiation-adapter`）
3. 图谱视图：`RadialGraphView` → `NegotiationGraph`
4. 默认视图：`useState<ProgressView>('timeline')` → `useState<ProgressView>('graph')`
5. 新增 DetailPanel 状态和交互回调（onNodeClick → 设 detail state → 显示 DetailPanel）
6. 删除旧 `RadialGraphView` 函数（305-472 行）

**NegotiationGraph 接入方式**：
```tsx
const negotiationState = useMemo(
  () => buildNegotiationState(events, phase),
  [events, phase],
);

// 图谱视图
<div style={{ width: '100%', maxWidth: 800 }}>
  <NegotiationGraph
    state={negotiationState}
    onNodeClick={handleNodeClick}
    onEdgeClick={handleEdgeClick}
    onTaskClick={handleTaskClick}
  />
</div>

// DetailPanel（右侧滑入）
<DetailPanel
  type={detailPanel.type}
  data={detailPanel.data}
  onClose={handleCloseDetail}
/>
```

**交互回调**：复用 NegotiationPage 的逻辑模式——
- 点击 Agent 节点 → 显示 offer 内容、共振分数、角色
- 点击 Center 节点 → 显示当前轮次、工具调用历史
- 点击 Demand 节点 → 显示 formulation 结果
- 点击 Task 节点 → 显示任务详情
- 点击边 → 显示交互类型和内容

### 文件 3: `website/app/store/[scene]/page.tsx`（微调）

**变更**：
- `NegotiationProgress` 的容器去掉 `padding: '16px 24px'` 的宽度限制
- 确保图谱区域有足够宽度（800px viewBox 自适应）

### 不改的文件

- `useStoreNegotiation.ts` — 不动，适配在消费端做
- `useStoreWebSocket.ts` — 不动
- `NegotiationGraph.tsx` 及所有子组件 — 不动，原样复用
- `DetailPanel.tsx` — 不动，原样复用
- `PlanOutput.tsx` / `TopologyView.tsx` — 不动（Plan 展示保持现有实现）

## 数据流验证

```
用户提交需求
  → startNegotiation() REST 调用
  → ws.connect(negId) WebSocket 连接
  → WS 事件逐个到达 → useStoreWebSocket.events[]
  → buildNegotiationState(events, phase) 适配转换    ← 新增
  → NegotiationGraph(state) 渲染图谱                  ← 替换
  → 用户点击节点 → DetailPanel 显示详情               ← 新增
```

**每一环数据来源确认**：
- ✅ WS 事件包含完整数据（formulation, agents+scores, offers+content, tool_calls+args, plan_json）
- ✅ NegotiationGraph 只读 state，不做数据请求
- ✅ DetailPanel 只读 data prop，不做数据请求
- ⚠️ `filtered_agents` 后端未传 → 适配函数给空数组，图谱不挂

## 不做的事情

- 不统一两套 hooks（P2，后续讨论）
- 不改 Store 后端 API（P1 min_score/filtered_agents，单独改）
- 不删 `/negotiation` 页面（保留为开发工具）
- 不改 NegotiationGraph 组件本身（零修改复用）

## 验收标准

1. App Store 场景页提交需求后，显示 800x600 的完整协商图谱
2. 图谱默认展示（不是时间线文字）
3. 共振波纹、节点出现、边生长、Center 脉冲动画全部正常
4. 点击任意节点/边 → DetailPanel 滑入显示详情
5. Center tool_call 动画队列顺序播放
6. Plan ready 后 task 节点出现在内环
7. 时间线视图仍可切换查看
8. `npm run build` 通过
