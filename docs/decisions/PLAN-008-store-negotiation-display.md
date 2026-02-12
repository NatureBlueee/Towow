# PLAN-008: App Store 协商展示重构

**日期**: 2026-02-12
**关联**: ADR-008, Issue 005
**状态**: 待确认

## 目标

将 App Store 的协商展示从 SVG 图谱改为 HTML/CSS 流程展示，解决布局失效和方案显示丢失问题。

## 变更总览

| # | 文件 | 类型 | 描述 |
|---|------|------|------|
| 1 | `website/app/store/page.tsx` | 修改 | PlanOutput 条件修复 |
| 2 | `website/components/store/NegotiationProgress.tsx` | 重写 | SVG 图谱 → HTML 流程展示 |
| 3 | `website/components/store/NegotiationProgress.module.css` | 新建 | 流程展示样式 + CSS 动画 |
| 4 | `website/app/store/[scene]/page.tsx` | 验证 | 确认 PlanOutput 条件已正确 |

**不改的文件**（明确列出）：
- `website/components/negotiation/graph/*` — `/negotiation` 页面继续使用
- `website/components/negotiation/PlanView.tsx` — PlanOutput 继续复用
- `website/components/negotiation/DetailPanel.tsx` — 继续复用
- `website/lib/store-negotiation-adapter.ts` — 暂保留（NegotiationProgress 不再使用它，但不删除以免影响其他潜在消费方）
- `website/hooks/useStoreNegotiation.ts` — 接口不变

## 变更详情

### 变更 1：PlanOutput 条件修复

**文件**: `website/app/store/page.tsx:108`
**类型**: Bug fix（契约不变，实现修复）

```tsx
// 修复前
{negotiation.planOutput && (

// 修复后（对齐场景页 store/[scene]/page.tsx:123）
{(negotiation.planOutput || negotiation.planJson || negotiation.phase === 'completed') && (
```

**链路验证**：
- `planOutput`: 来自 GET 轮询 `plan_output` 字段 ✓
- `planJson`: 来自 WS `plan.ready` 事件 OR GET 轮询 `plan_json` ✓
- `phase === 'completed'`: 来自 WS 事件 OR GET 轮询 ✓
- 三路覆盖，最早到达的那路就能触发渲染

### 变更 2：NegotiationProgress 重写

**文件**: `website/components/store/NegotiationProgress.tsx`
**类型**: 实现替换（组件接口不变，内部实现完全重写）

#### Props 接口（不变）

```typescript
interface NegotiationProgressProps {
  phase: NegotiationPhase;
  participants: StoreParticipant[];
  events: StoreEvent[];
  timeline: TimelineEntry[];
  graphState: GraphState;
  error: string | null;
  onReset: () => void;
}
```

两个消费方 (`store/page.tsx`, `store/[scene]/page.tsx`) 传入的 props 不变。

#### 内部结构：4 个区域

```
┌─────────────────────────────────────────────────────┐
│ 协商进度  [已完成]                                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ① PhaseSteps                                        │
│ ● 需求理解 ─── ● 共振 ─── ● 响应 ─── ● 协调 ─── ● 完成│
│                                                     │
│ ② AgentGrid (flexbox wrap, 任意数量)                  │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│ │无限循环│ │青春版 │ │代码农民│ │编译器 │ │Rust手│       │
│ │  64%  │ │  63% │ │  58% │ │  57% │ │  55% │       │
│ │ ✓已回应│ │ ✓已回应│ │ ✓已回应│ │ ✓已回应│ │ ✓已回应│       │
│ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘       │
│ ┌──────┐ ┌──────┐ ...自动换行                        │
│ │Alice │ │拉面全栈│                                   │
│ │  53% │ │  53% │                                   │
│ └──────┘ └──────┘                                   │
│                                                     │
│ ③ ActivityFeed (可折叠)                               │
│ ▸ Center 协调记录 (3)                                 │
│   • 追问 Agent-X                                     │
│   • 发现连接                                          │
│   • 输出方案                                          │
│                                                     │
│ [重新开始]                                            │
└─────────────────────────────────────────────────────┘
```

#### 区域 ① PhaseSteps

数据源：`phase` prop

| phase 值 | 步骤高亮 |
|----------|---------|
| submitting | 步骤 1 active |
| formulating | 步骤 1 active |
| resonating | 步骤 1 done, 2 active |
| offering | 步骤 1-2 done, 3 active |
| synthesizing | 步骤 1-3 done, 4 active |
| completed | 步骤 1-5 done |
| error | 最后一个 active 步骤变红 |

实现：`<div>` + flexbox row，每个步骤是 `<div>` + 圆点 + 标签 + 连接线。
CSS：`.done` 圆点实心，`.active` 圆点脉冲动画，默认灰色。

#### 区域 ② AgentGrid

数据源：`participants` prop (StoreParticipant[])

每个卡片显示：
- 名字（display_name，最多 6 字 + `..`）
- 共振分数（百分比）
- 状态：已回应（有 offer_content）/ 等待中
- 来源标识（source: secondme / json_file）

实现：`<div>` + `display: flex; flex-wrap: wrap; gap: 8px`。
卡片尺寸：固定宽 110px，内容高度自适应。
CSS 动画：新卡片 opacity 0→1 + translateY(8px)→0，stagger 延迟。

数量适应：
- 5 个以下：一行放完
- 5-10 个：自动两行
- 10-20 个：自动三四行
- 20+ 个：默认显示前 12 个 + "展开全部 (N)" 按钮

#### 区域 ③ ActivityFeed

数据源：`timeline` prop (TimelineEntry[])

分两部分：
- 主要事件（formulation, resonance, barrier, plan）始终显示
- Center 工具调用（tool type）可折叠

实现：已有 TimelineView 的逻辑基本可复用，调整样式。

#### 区域 ④ 去掉

方案展示由 PlanOutput 组件独立负责（在 NegotiationProgress 下方），不在 NegotiationProgress 内部。

#### 不再使用的依赖

NegotiationProgress 不再 import：
- `NegotiationGraph`（SVG 图谱组件）
- `buildNegotiationState`（adapter 函数）
- `DetailPanelContentType`（图谱详情类型）

仍然使用：
- `DetailPanel`（点击 Agent 卡片 → 侧滑详情）

### 变更 3：CSS Module

**文件**: `website/components/store/NegotiationProgress.module.css`（新建）

动画策略：
- **Phase 步骤**：`transition: background-color 0.3s, color 0.3s` — 步骤状态变化时平滑过渡
- **Agent 卡片入场**：`@keyframes cardEnter { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: translateY(0) } }` + `animation-delay` stagger
- **时间线条目**：`transition: opacity 0.2s` — 新条目淡入
- **没有**：animation queue、converging particles、wave ripple、SVG 相关动画

## 变更链路验证

### 链路 1：NegotiationProgress 渲染
```
store/page.tsx → NegotiationProgress(props)
  props 不变 → 内部实现替换
  不影响消费方 ✓
```

### 链路 2：PlanOutput 显示
```
WS plan.ready → planJson 立即可用 → phase='completed'
                                   ↓
store/page.tsx 条件: planOutput || planJson || completed
  任一为 true → PlanOutput 渲染 ✓
```

### 链路 3：DetailPanel 复用
```
AgentGrid 卡片点击 → setDetailPanel({type: 'agent', data: {...}})
  → DetailPanel 侧滑出现 ✓
  DetailPanel 接口不变 ✓
```

## 消费方验证

| 消费方 | 影响 | 处理 |
|--------|------|------|
| `store/page.tsx` | NegotiationProgress 接口不变 | 无需修改 |
| `store/[scene]/page.tsx` | NegotiationProgress 接口不变 | 无需修改 |
| `/negotiation` 页面 | 不使用 NegotiationProgress | 不受影响 |

## 实施顺序

1. **先修 PlanOutput 条件**（1 行改动，立即生效）
2. **新建 CSS Module**
3. **重写 NegotiationProgress**（内部实现替换，props 接口保持）
4. **验证场景页**
5. **前端 build 验证**

## Skill 调度

| 步骤 | Skill |
|------|-------|
| CSS 设计 + 布局 | `ui-ux-pro-max` |
| 组件实现 | `towow-dev` |
| 构建验证 | `towow-dev` |
