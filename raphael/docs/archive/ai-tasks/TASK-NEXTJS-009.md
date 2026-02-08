# TASK-NEXTJS-009: 首页集成

## 任务元信息

- **任务 ID**: TASK-NEXTJS-009
- **Beads ID**: `towow-75y`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 3 小时
- **状态**: TODO

---

## 1. 目标

将所有首页组件集成到 `app/page.tsx`，完成首页的完整实现。

---

## 2. 输入

- `ToWow - 几何花园 V1.html` 完整文件
- TASK-NEXTJS-007 产出的首页组件
- TECH-NEXTJS-MIGRATION-v5.md 第 6.2 节的首页数据结构

---

## 3. 输出

- `app/page.tsx` - 首页页面
- `app/layout.tsx` - 根布局（更新）
- `lib/constants.ts` - 首页数据

---

## 4. 验收标准

### 4.1 页面结构验收

- [ ] NoiseTexture 覆盖层
- [ ] GridLines 背景网格
- [ ] Hero 区块
- [ ] 6 个 ContentSection 区块
- [ ] NetworkJoin 区块
- [ ] Footer（home 变体）

### 4.2 视觉验收

- [ ] 与原 HTML 视觉效果 100% 一致
- [ ] 所有动画正常播放
- [ ] 所有 hover 效果正常
- [ ] 所有链接可点击

### 4.3 数据验收

- [ ] 所有文案与原 HTML 一致
- [ ] 所有链接指向正确
- [ ] 所有图标正确显示

---

## 5. 实现步骤

### 5.1 更新 app/layout.tsx

```typescript
// app/layout.tsx
import { NoiseTexture } from '@/components/layout/NoiseTexture';
import { GridLines } from '@/components/layout/GridLines';
import './globals.css';

export const metadata = {
  title: 'ToWow - Geometric Garden',
  description: '为 Agent 重新设计的互联网',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <head>
        <link
          href="https://cdnjs.cloudflare.com/ajax/libs/remixicon/4.6.0/remixicon.min.css"
          rel="stylesheet"
        />
      </head>
      <body>
        <NoiseTexture />
        <GridLines />
        {children}
      </body>
    </html>
  );
}
```

### 5.2 创建 lib/constants.ts

```typescript
// lib/constants.ts

export const HOME_SECTIONS = [
  {
    id: 'attention-to-value',
    title: '从注意力到价值：<br>互联网的下一次进化',
    content: `今天的互联网建立在"注意力经济"之上。平台通过免费服务获取你的注意力，再将其作为广告库存出售。这种模式导致了信息茧房、算法成瘾和隐私侵犯。
    <br><br>
    当 Agent 成为你的代理人，它不看广告，不被情绪劫持，只为你的利益服务。ToWow 正在构建的基础设施，就是为了支持这种从"眼球争夺"到"价值交换"的根本性转变。`,
    linkText: '深入阅读：从注意力到价值',
    linkHref: '/articles/attention-to-value',
    gridColumn: '2 / 7',
  },
  {
    id: 'negotiation-vs-search',
    title: '协商创造，而非搜索匹配',
    content: `现在的搜索是"在一堆已有的选项中找一个最接近的"。但真实世界的需求往往是独特且复杂的。
    <br><br>
    在 ToWow 网络中，Agent 不只是检索信息，而是通过协议（Protocol）进行即时协商。想去旅行？你的 Agent 会与航司、酒店、本地导游的 Agent 谈判，为你组合出一个独一无二的行程，甚至为你定制价格。`,
    linkText: '深入阅读：协商创造 vs 搜索匹配',
    linkHref: '/articles/negotiation-vs-search',
    gridColumn: '7 / 12',
  },
  // ... 更多区块数据
];

export const NETWORK_NODES = [
  {
    id: 'hackathon',
    icon: 'ri-terminal-box-line',
    label: '黑客松',
    color: 'var(--c-primary)',
    position: { top: '25%', left: '18%' },
    animationDelay: '0s',
  },
  {
    id: 'ai-community',
    icon: 'ri-brain-line',
    label: 'AI 社区',
    color: 'var(--c-secondary)',
    position: { top: '15%', left: '33%' },
    animationDelay: '1s',
  },
  {
    id: 'builder',
    icon: 'ri-hammer-line',
    label: '共建者',
    color: '#333',
    position: { top: '10%', left: '48%' },
    animationDelay: '0.5s',
    isSquare: true,
  },
  {
    id: 'indie-dev',
    icon: 'ri-code-s-slash-line',
    label: '独立开发者',
    color: 'var(--c-accent)',
    position: { top: '20%', right: '33%' },
    animationDelay: '2s',
  },
  {
    id: 'enterprise',
    icon: 'ri-building-2-line',
    label: '传统企业',
    color: 'var(--c-detail)',
    position: { top: '30%', right: '18%' },
    animationDelay: '1.5s',
  },
];
```

### 5.3 创建 app/page.tsx

```typescript
// app/page.tsx
import { Hero } from '@/components/home/Hero';
import { ContentSection } from '@/components/home/ContentSection';
import { NetworkJoin } from '@/components/home/NetworkJoin';
import { Footer } from '@/components/layout/Footer';
import { Shape } from '@/components/ui/Shape';
import { HOME_SECTIONS, NETWORK_NODES } from '@/lib/constants';

export default function HomePage() {
  return (
    <div className="page-container">
      {/* Hero */}
      <Hero
        title={
          <>
            <span className="en-font">ToWow</span>：为{' '}
            <span className="en-font">Agent</span> 重新设计的互联网
          </>
        }
        subtitle="当每个人都有了自己的 AI Agent，它们之间需要一个开放的协作网络——让你的 Agent 不止于本地助手，而是帮你链接世界的经济代表。"
        primaryAction={{ label: '加入网络', href: '#' }}
        secondaryAction={{ label: '了解我们的思考', href: '#' }}
      />

      {/* Content Sections */}
      {HOME_SECTIONS.map((section, index) => (
        <ContentSection
          key={section.id}
          title={section.title}
          content={section.content}
          linkText={section.linkText}
          linkHref={section.linkHref}
          gridColumn={section.gridColumn}
        >
          {/* 每个 section 的几何装饰 */}
          {renderSectionDecorations(index)}
        </ContentSection>
      ))}

      {/* Network Join */}
      <NetworkJoin nodes={NETWORK_NODES} />

      {/* Footer */}
      <Footer variant="home" />
    </div>
  );
}

function renderSectionDecorations(index: number) {
  // 根据 index 返回不同的几何装饰
  // 参考原 HTML 中每个 section 的装饰配置
}
```

---

## 6. 依赖关系

### 6.1 硬依赖

- TASK-NEXTJS-007: 首页组件

### 6.2 接口依赖

无

### 6.3 被依赖

- TASK-NEXTJS-011: 视觉 QA

---

## 7. 技术说明

### 7.1 几何装饰配置

每个 ContentSection 的几何装饰不同，需要根据原 HTML 精确配置：

| Section | 装饰配置 |
|---------|----------|
| 1 | 右侧：绿色圆形 + 杏色方形 |
| 2 | 左侧：紫色三角形 + 灰绿圆形 |
| 3 | 中心：紫色圆环 + 绿色方形 |
| 4 | 右侧：多个渐变大小的圆形 |
| 5 | 左侧：紫色方形 + 绿色圆形 + 黑色方形 |
| 6 | 中心：同心圆环 |

### 7.2 页面容器样式

```css
.page-container {
  width: 100%;
  position: relative;
  overflow: hidden;
}
```

---

## 8. 注意事项

- 确保所有文案与原 HTML 完全一致
- 几何装饰的位置和大小需要精确匹配
- 测试所有链接是否正确
- 测试页面滚动性能
