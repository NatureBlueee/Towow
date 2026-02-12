# ADR-008: App Store 协商展示重构——从图谱回归流程

**日期**: 2026-02-12
**状态**: 已批准
**关联**: Issue 005, ADR-003（本 ADR 替代 ADR-003 在 App Store 的实现）

## 背景

ADR-003 决策了"图谱优先布局"(Graph-First Layout)，用 800×600 SVG + 垂直流布局展示协商过程。实施后发现**该设计在 App Store 场景下失效**：

1. **布局数学不可能**：15 个 Agent（r=30, 直径 60px）在 540px 水平区间排列，间距 38.6px < 直径 60px，必然重叠
2. **方案显示丢失**：PlanOutput 的显示条件只检查 GET 轮询数据，WS 事件先到但不触发渲染
3. **复杂度失控**：6 层数据转换（Store 事件 → adapter → NegotiationState → computeLayout → SVG → 6 子组件）让问题难以定位和修复

核心矛盾：**SVG 图谱是空间布局问题，协商展示是时序流问题。用空间工具解决时序问题，注定不匹配。**

## 选项分析

### 选项 A：修补现有 SVG 图谱
- 缩小节点半径（r=30→12）、多行排列、动态 viewBox
- 优势：改动小，保留已有代码
- 劣势：治标不治本。10 节点以下看起来空旷，15+ 仍然拥挤。"空间布局解决时序问题"的根本矛盾不变

### 选项 B：App Store 专属 HTML/CSS 流程展示（选定）
- 用 HTML 布局承载"阶段流 + 参与者 + 交互 + 结果"
- 优势：flexbox/grid 天然支持任意数量元素；每个职责有独立区域；简单可维护
- 劣势：不再有"图谱"视觉效果

### 选项 C：用成熟图谱库（D3, react-flow）
- 优势：专业布局算法
- 劣势：引入大依赖；仍然是用图谱思维解决流程问题；overkill

## 决策

**选项 B**：App Store 协商展示回归流程本质，用 HTML/CSS 组件替代 SVG 图谱。

### 核心原则

**协商可视化的本质是"阶段流 + 参与者 + 结果"，不是"图谱"。**

协议层的 7 个事件是**时序流**——有明确的阶段顺序。用户需要知道的是：
1. 现在到哪一步了？（阶段）
2. 谁参与了？（参与者）
3. Center 做了什么？（交互）
4. 最终方案是什么？（结果）

这四个问题映射到四个**独立区域**，不需要空间坐标，不需要边，不需要 SVG。

### 本质定义（接口层）

NegotiationProgress 组件的**本质**是：

```
输入: 协商事件流 (StoreEvent[]) + 当前阶段 (phase) + 参与者列表 (participants[])
输出: 四个可视区域
  1. PhaseBar: 当前阶段指示 (formulating → resonating → offering → synthesizing → completed)
  2. AgentGrid: 参与者网格 (任意数量, 每个显示名字 + 分数 + 是否已回应)
  3. ActivityFeed: Center 交互记录 (tool_call 列表, 可展开)
  4. PlanSection: 方案展示 (复用 PlanView)
```

**每个区域独立渲染**，不共享坐标系，不互相依赖位置。

### 与 ADR-003 的关系

- ADR-003 的决策（图谱优先布局）在 `/negotiation` 页面保持不变
- App Store 不再使用 NegotiationGraph，用自己的 HTML 流程展示
- `store-negotiation-adapter.ts` 不再需要（不再需要转换为 NegotiationState）
- DetailPanel 零修改复用（点击参与者 / 任务 → 侧滑详情）

## 架构原则对齐

- **0.2 本质与实现分离**：先定义"展示什么"（阶段、参与者、交互、结果），再决定"怎么展示"
- **0.7 复杂性从简单规则生长**：四个独立区域，各自用最简单的布局（flexbox wrap / 列表 / 卡片）
- **0.5 代码保障 > Prompt 保障**：PlanOutput 显示条件必须覆盖所有数据来源（WS + REST），不依赖"轮询一定比 WS 先到"的假设

## 影响范围

| 模块 | 变更 |
|------|------|
| `website/components/store/NegotiationProgress.tsx` | 重写：HTML 流程展示替代 NegotiationGraph |
| `website/app/store/page.tsx` | 修复 PlanOutput 条件 |
| `website/app/store/[scene]/page.tsx` | 确认条件已正确（验证） |
| `website/lib/store-negotiation-adapter.ts` | 可能不再需要（NegotiationProgress 直接消费 StoreEvent[]） |
| `website/components/negotiation/graph/*` | **不改**（/negotiation 页面继续使用） |
| `website/components/negotiation/PlanView.tsx` | **不改**（继续复用） |
| `website/components/negotiation/DetailPanel.tsx` | **不改**（继续复用） |
