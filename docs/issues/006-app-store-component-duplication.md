# Issue 006: App Store 协商组件重复与数据断裂

**日期**: 2026-02-12
**发现方式**: ADR-003 合规审计后的跨系统交叉检查
**严重程度**: P0（组件重复）+ P1（数据断裂）
**状态**: P0 全部已修 | P1/P2 待处理

## 问题描述

Feature 004（协商图谱可视化）在 `components/negotiation/` 实现了完整的图谱组件体系，但 App Store（`components/store/`）作为同一 V1 协议的另一个消费方，**完全没有同步更新**，仍使用独立的简化实现。

这是典型的**并行 Agent 接缝盲区**——Feature 004 的开发范围只覆盖了 Negotiation 页面，App Store 被遗漏。

## 诊断详情

### 问题 1：两套独立的协商可视化（P0）

| 维度 | App Store (`components/store/`) | Negotiation (`components/negotiation/`) |
|------|------|------|
| 径向图谱 | `NegotiationProgress.tsx` 自有 RadialGraphView (473行) | `NegotiationGraph.tsx` 完整图谱 (435行) |
| 任务拓扑 | `TopologyView.tsx` 用 `@/lib/topology-layout` 库 | `PlanView.tsx` 自己实现了 computeTopologyLayout |
| Hooks | `useStoreNegotiation` | `useNegotiationStream` |
| 交互能力 | 无（纯展示） | 完整（点击节点/边/任务 -> DetailPanel） |

App Store 的 `NegotiationProgress.tsx` 有自己的 `RadialGraphView`，完全没有复用 `NegotiationGraph` 及其子组件（`DemandNode`、`AgentNode`、`CenterNode`、`ResonanceEdge`、`InteractionEdge`）。

### 问题 2：拓扑布局算法写了两遍（P0，已修）

- `website/lib/topology-layout.ts` — Kahn 算法的共享库函数（已存在）
- `website/components/store/TopologyView.tsx` — 正确使用了这个库
- `website/components/negotiation/PlanView.tsx` — 自己重写了一遍（51-146行，递归 DFS），没用库

**差异**：
- 共享库：Kahn's BFS，按 assigneeId 排序同层节点，循环检测返回 null
- PlanView 旧实现：递归 DFS，无排序，visited 集合防环

**修复**：PlanView.tsx 改为使用 `@/lib/topology-layout` 共享库，通过适配器映射 PlanJsonTask → TaskNode 和 LayoutNode → TaskPosition。保留 PlanView 的渲染层（Framer Motion 动画、Bezier 曲线、foreignObject 卡片），只替换布局计算。

### 问题 3：App Store 后端数据断裂（P1）

| 字段 | V1 Engine | Store 后端 | 状态 |
|------|-----------|-----------|------|
| `plan_json` | 有 | 正确传递 | 正常 |
| `k_star` | 参数化 | 自动 `len(candidates)` | 用户不可定制 |
| `min_score` | 参数化 | 完全缺失 | 数据断裂 |
| `filtered_agents` | 事件中有 | API 响应缺失 | 前端拿不到 |

Store 后端的 `NegotiateRequest` 缺少 `min_score` 和 `k_star` 字段，`NegotiationResponse` 缺少 `filtered_agents`。

### 问题 4：两套 Hooks 各自为战（P2）

- `useStoreNegotiation` — App Store 用，REST 轮询
- `useNegotiationStream` — Negotiation 页面用，WebSocket 事件流

两套独立的事件处理逻辑，状态结构不同，演进方向不同。

## 根因分析

1. **Feature 004 的范围定义**没有包含 App Store —— 只定义了 Negotiation 页面的图谱可视化
2. **App Store 和 Negotiation 页面的产品形态不同**（App Store 是场景入口 + 简化展示，Negotiation 是完整协商交互），导致"自然觉得应该分开"
3. **并行开发时没有跨 Track 检查**——Feature 004 的 Track 只看了 `components/negotiation/`，没检查 `components/store/`

## 已完成的修复

### P0 拓扑重复（已修）

`PlanView.tsx` 删除自有的 `computeTopologyLayout`（95 行递归 DFS），替换为使用 `@/lib/topology-layout` 共享库的适配器：
- `PlanJsonTask[]` → `TaskNode[]` 映射
- `computeLayeredLayout(taskNodes, 220, 100)` 调用
- `LayoutNode[]` → `TaskPosition[]` + `LayoutEdge[]` → `TopologyEdge[]` 回映射
- 循环检测 fallback（单列布局）

Build 验证通过。

### P0 图谱复用（已修，PLAN-006）

App Store 的 `NegotiationProgress.tsx` 完整复用 `NegotiationGraph` + `DetailPanel`：
- 新增 `website/lib/store-negotiation-adapter.ts`：`StoreEvent[]` → `NegotiationState` 适配器
- `RadialGraphView`（168 行简化径向图）删除，替换为 `NegotiationGraph`（800x600 全交互）
- `DetailPanel` 零修改复用，点击节点/边 → 右侧滑入详情
- 默认视图从"时间线"改为"图谱"，时间线仍可切换
- 场景页容器 padding 调整（24px → 8px）适配 800px 图谱

Build 验证通过。

## 待处理

### P1：Store 后端 API 扩展

- `NegotiateRequest` 加 `min_score` 和 `k_star` 参数
- `NegotiationResponse` 加 `filtered_agents` 字段
- 涉及文件：`apps/app_store/backend/routers.py`

### P2：Hooks 统一

长期应该考虑将 `useStoreNegotiation` 和 `useNegotiationStream` 统一为一套事件处理核心，但这依赖 P0 组件复用方向的决策。

## 教训

1. **跨消费方同步检查**：每次改协议层组件（事件处理、图谱可视化），必须检查所有消费方（Negotiation 页面 + App Store + 未来的 MCP）
2. **共享库先行**：拓扑布局这类纯计算逻辑，应该在第一次写的时候就提取到 `@/lib/` 作为共享库，而不是各组件自己实现
3. **Feature scope 必须覆盖所有消费方**：Feature 004 的 scope 应该包含"检查 App Store 是否受影响"这一步
