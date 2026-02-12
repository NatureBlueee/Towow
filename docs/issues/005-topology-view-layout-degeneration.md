# Issue 005: TopologyView 布局退化 — 无依赖任务堆叠成垂直单列

**日期**: 2026-02-12
**状态**: 已修复
**严重度**: P1（用户直接可见的视觉问题）
**关联**: Issue 004（Store 协商展示层缺陷）

## 现象

App Store 协商完成后，"协商方案" 区块中的 TopologyView：
- 所有任务节点堆叠在左侧成垂直单列
- 右侧大面积空白（仅用 ~400px 宽度，容器 ~800px+）
- 节点内容被截断为省略号，看不清任务信息
- SVG 高度爆炸（8 个节点 → 910px 高），比例失调
- 没有视觉层次，不像任务拓扑

## 根因

`topology-layout.ts` 使用 Kahn 拓扑排序做分层布局：

```
x = layer * layerWidth    // 按依赖层级水平分布
y = index * nodeHeight     // 同层内垂直排列
```

**当所有任务的 `prerequisites` 为空时，全部落在 layer 0：**
- x = 0 × 200 = 0（全靠左）
- y = 0, 100, 200, ..., 700（垂直堆叠）
- 布局宽度 = 1 × 200 = 200px → SVG 宽度 400px
- 布局高度 = 8 × 100 = 800px → SVG 高度 910px

### 为什么 prerequisites 为空

两条数据来源都可能没有依赖关系：

1. **`ensureTopologyPlan()` fallback**：前端兜底构造的 plan_json，`prerequisites: []` 硬编码为空
2. **Center output_plan 真实输出**：Center 不一定总是生成带依赖关系的任务

### 这是退化问题，不是 bug

布局算法为 DAG（有向无环图）设计。当输入退化为"无边图"时，算法退化为单列——这在数学上是正确的，但在 UI 上完全不可用。

## 修复

### 1. `topology-layout.ts` — 添加网格布局模式

当 `maxLayer === 0`（所有节点在同一层）时，自动切换为网格布局：
- 列数 = min(ceil(sqrt(n)), 4)
- 节点均匀分布在二维网格中

8 个无依赖任务的效果：
- 修复前：1 列 × 8 行 → 400×910px
- 修复后：3 列 × 3 行 → 756×396px

### 2. `TopologyView.tsx` — 改用 foreignObject 渲染卡片

SVG 原生 `<text>` 元素无法支持多行文本、文本溢出截断等 HTML 排版能力。
改用 `<foreignObject>` 嵌入 HTML 卡片：
- 左侧色带标识 assignee
- 头像 + 标题 + 执行者名
- 任务描述（2 行截断）
- 选中高亮 + 关联节点变暗

## 教训

**布局算法必须有退化处理。**

设计布局算法时，不能只考虑理想输入（有丰富依赖边的 DAG）。当输入退化为特殊情况（无边、单节点、全连接）时，布局不能跟着退化成不可用的形态。

这和协议设计原则一样——代码保障 > 假设保障。不能假设"Center 总会生成有意义的 prerequisites"。

## 待跟进

- **动画 Skill 建立**：统一前端动画设计标准（单独 Issue/ADR）
- **NegotiationGraph CSS-only 重写**：删除 framer-motion，按动画 Skill 原则重做
