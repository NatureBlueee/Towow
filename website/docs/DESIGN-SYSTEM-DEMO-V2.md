# ToWow Demo V2 - Design System

> **Note**: This design doc references legacy paths. The V2 components have been migrated to
> `components/demand-negotiation/` and the page route is now `/apps/demand-negotiation`.
> Old versions are archived in `archive/experience-v2/`.

## Overview

ToWow Demo 的新交互架构，包含5个阶段的沉浸式体验流程。

## Design Tokens

### Colors (继承现有系统)

```css
--c-primary: #D4B8D9;          /* 暖紫/玫瑰紫 */
--c-secondary: #D4F4DD;        /* 薄荷绿 */
--c-accent: #FFE4B5;           /* 蜜桃橙 */
--c-detail: #E8F3E8;           /* 淡绿 */
--c-warm: #F9A87C;             /* 珊瑚橙 */
--c-bg: #F8F6F3;               /* 米白背景 */

/* 新增 - Agent 状态颜色 */
--c-agent-active: #22C55E;     /* 活跃状态 - 绿色 */
--c-agent-speaking: #3B82F6;   /* 发言中 - 蓝色 */
--c-agent-waiting: #94A3B8;    /* 等待中 - 灰色 */
--c-insight: #8B5CF6;          /* 洞察卡片 - 紫色 */
--c-transform: #F59E0B;        /* 转变卡片 - 橙色 */
--c-combine: #10B981;          /* 组合卡片 - 绿色 */
--c-confirm: #3B82F6;          /* 确认卡片 - 蓝色 */
```

### Typography

```css
/* 继承现有字体系统 */
--f-cn-head: 'NotoSansHans-Medium', 'PingFang SC', sans-serif;
--f-cn-body: 'NotoSansHans-Regular', 'PingFang SC', sans-serif;

/* 新增 - 数据展示字体 */
--f-mono: 'SF Mono', 'Menlo', monospace;
```

### Spacing & Layout

```css
/* 阶段指示器高度 */
--stage-indicator-height: 56px;

/* 网络图视图 */
--network-node-size: 48px;
--network-node-size-lg: 80px;
--network-connection-width: 2px;

/* 卡片间距 */
--card-gap: 16px;
```

## Component Architecture

### 1. Stage Indicator (阶段指示器)

```
[需求] → [响应] → [协商] → [方案] → [汇总]
```

- 固定在顶部
- 当前阶段高亮
- 点击可跳转（已完成的阶段）

### 2. Stage 1: Requirement Input (需求输入)

Components:
- `RequirementInput` - 主输入框
- `ExampleRequirements` - 示例需求列表

Layout:
```
┌─────────────────────────────────────┐
│         ToWow Experience            │
│      体验 AI Agent 协作网络          │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐    │
│  │  描述你的需求...             │    │
│  │                             │    │
│  │                    [提交]   │    │
│  └─────────────────────────────┘    │
│                                     │
│  试试这些示例：                      │
│  • 找技术合伙人...                   │
│  • 手工皮具工作室...                 │
│  • 组织AI主题聚会...                 │
└─────────────────────────────────────┘
```

### 3. Stage 2: Agent Response (Agent响应 - 网络图视图)

Components:
- `NetworkGraph` - 网络图容器
- `CenterNode` - 中心需求节点
- `AgentNode` - Agent节点
- `ConnectionLine` - 连接线
- `AgentTooltip` - Agent详情悬浮卡片

Layout:
```
┌─────────────────────────────────────┐
│                                     │
│           ○ Agent1                  │
│          ╱                          │
│    ○────●────○                      │
│   Agent2  需求  Agent3              │
│          ╲                          │
│           ○ Agent4                  │
│                                     │
├─────────────────────────────────────┤
│  7个Agent响应了你的需求  [开始协商]  │
└─────────────────────────────────────┘
```

Animation:
- Agent节点逐个出现（stagger: 300ms）
- 连接线从中心向外延伸
- 初始响应文字淡入淡出

### 4. Stage 3: Negotiation (协商过程 - 双栏视图)

Components:
- `NegotiationLayout` - 双栏布局
- `DynamicNetworkGraph` - 动态网络图（左侧）
- `EventCardStream` - 事件卡片流（右侧）
- `InsightCard` - 洞察卡片
- `TransformCard` - 转变卡片
- `CombineCard` - 组合卡片
- `ConfirmCard` - 确认卡片
- `NegotiationControls` - 控制按钮

Layout:
```
┌──────────────────┬──────────────────┐
│                  │                  │
│   动态网络图      │   事件卡片流      │
│                  │                  │
│   ○──●──○        │  ┌────────────┐  │
│      │           │  │ 💡 洞察    │  │
│      ○           │  └────────────┘  │
│                  │  ┌────────────┐  │
│   (连线动画)      │  │ 🔄 转变    │  │
│                  │  └────────────┘  │
│                  │                  │
├──────────────────┴──────────────────┤
│  [加速]  [暂停]  [跳到结果]          │
└─────────────────────────────────────┘
```

### 5. Stage 4: Proposal (方案展示 - 对比视图)

Components:
- `ProposalComparison` - 对比布局
- `OriginalRequirement` - 原始需求卡片
- `ProposedSolution` - 协商方案卡片
- `StepItem` - 方案步骤项
- `CostComparison` - 成本对比
- `ParticipantList` - 参与Agent列表

Layout:
```
┌──────────────────┬──────────────────┐
│   原始需求        │   协商后方案      │
├──────────────────┼──────────────────┤
│                  │                  │
│  预期投入: ¥50k  │  Step 1: ...     │
│  风险: 高        │  Step 2: ...     │
│                  │  Step 3: ...     │
│                  │                  │
├──────────────────┴──────────────────┤
│  原始成本: ¥50,000  →  新方案: ¥8,000│
├─────────────────────────────────────┤
│  参与方案的Agent: [头像] [头像] ...  │
└─────────────────────────────────────┘
```

### 6. Stage 5: Summary (过程汇总 - 全景视图)

Components:
- `SummaryLayout` - 全景布局
- `NegotiationTimeline` - 协商时间线（横向）
- `ValueFlowChart` - 价值流向图（纵向）
- `KeyInsightCards` - 关键洞察卡片组
- `ActionButtons` - 操作按钮组

Layout:
```
┌─────────────────────────────────────┐
│  协商时间线                          │
│  ●──────●──────●──────●──────●      │
│  需求   响应   协商   方案   完成    │
├─────────────────────────────────────┤
│  价值流向图                          │
│  [可视化图表]                        │
├─────────────────────────────────────┤
│  ┌─────┐ ┌─────┐ ┌─────┐           │
│  │关键  │ │认知  │ │意外  │           │
│  │洞察  │ │转变  │ │发现  │           │
│  └─────┘ └─────┘ └─────┘           │
├─────────────────────────────────────┤
│  [重新开始]  [分享案例]  [了解更多]   │
└─────────────────────────────────────┘
```

## Animation Guidelines

### Timing

```css
--duration-fast: 150ms;      /* 微交互 */
--duration-normal: 300ms;    /* 状态变化 */
--duration-slow: 500ms;      /* 页面过渡 */
--duration-stagger: 100ms;   /* 列表项延迟 */
```

### Easing

```css
--ease-out: cubic-bezier(0.33, 1, 0.68, 1);
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
--ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
```

### Key Animations

1. **Node Appear**: scale(0) → scale(1) + fadeIn
2. **Connection Draw**: strokeDashoffset animation
3. **Card Slide**: translateY(20px) → translateY(0)
4. **Pulse**: scale(1) → scale(1.1) → scale(1)

## Accessibility

- Focus states on all interactive elements
- Keyboard navigation support
- `prefers-reduced-motion` support
- ARIA labels for network graph elements
- Color contrast ratio >= 4.5:1

## File Structure

```
components/experience-v2/
├── StageIndicator/
│   ├── StageIndicator.tsx
│   └── StageIndicator.module.css
├── Stage1-Input/
│   ├── RequirementInput.tsx
│   ├── ExampleRequirements.tsx
│   └── Stage1.module.css
├── Stage2-Response/
│   ├── NetworkGraph.tsx
│   ├── AgentNode.tsx
│   ├── CenterNode.tsx
│   ├── ConnectionLine.tsx
│   └── Stage2.module.css
├── Stage3-Negotiation/
│   ├── NegotiationLayout.tsx
│   ├── DynamicNetworkGraph.tsx
│   ├── EventCardStream.tsx
│   ├── EventCard.tsx
│   └── Stage3.module.css
├── Stage4-Proposal/
│   ├── ProposalComparison.tsx
│   ├── StepItem.tsx
│   ├── CostComparison.tsx
│   └── Stage4.module.css
├── Stage5-Summary/
│   ├── SummaryLayout.tsx
│   ├── NegotiationTimeline.tsx
│   ├── KeyInsightCards.tsx
│   └── Stage5.module.css
└── shared/
    ├── types.ts
    ├── hooks/
    │   ├── useStageNavigation.ts
    │   └── useNetworkAnimation.ts
    └── utils/
        └── animationHelpers.ts
```

## Implementation Status

### Completed Components

| Component | File | Status |
|-----------|------|--------|
| StageIndicator | `StageIndicator/StageIndicator.tsx` | Done |
| RequirementInput | `Stage1-Input/RequirementInput.tsx` | Done |
| NetworkGraph | `Stage2-Response/NetworkGraph.tsx` | Done |
| NegotiationLayout | `Stage3-Negotiation/NegotiationLayout.tsx` | Done |
| ProposalComparison | `Stage4-Proposal/ProposalComparison.tsx` | Done |
| SummaryLayout | `Stage5-Summary/SummaryLayout.tsx` | Done |
| ExperienceV2Page | `ExperienceV2Page.tsx` | Done |

### Page Route

- URL: `/experience-v2`
- File: `app/experience-v2/page.tsx`

### Usage

```tsx
import { ExperienceV2Page } from '@/components/experience-v2';

// In your page component
export default function Page() {
  return <ExperienceV2Page />;
}
```

### Customization

To customize the demo data, modify the mock data in `ExperienceV2Page.tsx`:

- `MOCK_AGENTS` - Agent list with their info
- `MOCK_EVENTS` - Negotiation events
- `MOCK_PROPOSAL` - Final proposal data
- `MOCK_INSIGHTS` - Key insights for summary

## Design Decisions

### Why CSS Modules?

- Scoped styles prevent conflicts
- Works well with Next.js
- No runtime overhead
- Easy to maintain

### Why No External Animation Library?

- CSS animations are sufficient for this use case
- Smaller bundle size
- Better performance
- `prefers-reduced-motion` support built-in

### Color Choices

- Event card colors follow semantic meaning:
  - Purple (#8B5CF6) for insights - wisdom, creativity
  - Orange (#F59E0B) for transforms - change, energy
  - Green (#10B981) for combinations - growth, harmony
  - Blue (#3B82F6) for confirmations - trust, stability

### Responsive Strategy

- Mobile-first approach
- Breakpoints: 480px, 768px
- Network graph scales down on mobile
- Dual-column layout stacks on tablet
