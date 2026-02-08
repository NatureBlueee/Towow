# ToWow 静态页面 Next.js 迁移技术方案

## 文档元信息

- **文档类型**: 技术方案 (TECH)
- **版本**: v5
- **状态**: DRAFT
- **创建日期**: 2026-01-29
- **关联项目**: ToWow Website
- **关联文档**: `.ai/NEXTJS-MIGRATION-PLAN.md`

---

## 1. 目标与范围

### 1.1 核心目标

将 ToWow 现有的静态 HTML 页面迁移到 Next.js 项目，实现：

1. **组件化**: 将重复的 UI 元素抽象为可复用组件
2. **模块化**: CSS 样式模块化，避免全局污染
3. **可维护性**: 清晰的目录结构和代码组织
4. **视觉一致性**: 100% 还原原有设计，不改变任何视觉效果

### 1.2 范围边界

| 范围内 | 范围外 |
|--------|--------|
| 首页（几何花园）迁移 | 响应式设计（保持 1920px 固定宽度） |
| 6 篇文章页面迁移 | CMS 集成 |
| CSS 变量系统建立 | 国际化 (i18n) |
| 组件库搭建 | SEO 优化（后续迭代） |
| 静态数据管理 | 用户认证系统 |

### 1.3 成功标准

- [ ] 所有页面视觉效果与原 HTML 100% 一致
- [ ] 组件复用率 > 60%
- [ ] 无 CSS 全局污染
- [ ] Lighthouse 性能分数 > 80

---

## 2. 现状分析

### 2.1 源文件清单 [VERIFIED]

基于 `/Users/nature/个人项目/Towow/raphael/html-widgets (2)/` 目录：

| 文件名 | 类型 | 行数 | 说明 |
|--------|------|------|------|
| `ToWow - 几何花园 V1.html` | 首页 | 569 | 主页面，包含 Hero + 7 个内容区块 + Footer |
| `从注意力到价值 - ToWow深度阅读.html` | 文章 | 857 | 文章模板，包含 Header + Hero + TOC + Content + Related |
| `协商创造 vs 搜索匹配 - ToWow深度阅读.html` | 文章 | - | 同上 |
| `为什么开放是唯一的选择 - ToWow深度阅读.html` | 文章 | - | 同上 |
| `为什么个体才是网络的主角 - ToWow深度阅读.html` | 文章 | - | 同上 |
| `端侧Agent的爆发，然后呢 - ToWow深度阅读.html` | 文章 | - | 同上 |
| `道生一：极简的技术架构 - ToWow深度阅读.html` | 文章 | - | 同上 |

### 2.2 设计系统分析 [VERIFIED]

基于 `ToWow - 几何花园 V1.html:19-40` 提取的设计系统：

#### 颜色系统
```css
--c-primary: #CBC3E3;    /* Wisteria - 主色调，紫藤色 */
--c-secondary: #D4F4DD;  /* Lime - 次要色，青柠色 */
--c-accent: #FFE4B5;     /* Apricot - 强调色，杏色 */
--c-detail: #E8F3E8;     /* Sage Green - 细节色，鼠尾草绿 */
--c-bg: #EEEEEE;         /* Fog Gray - 背景色，雾灰 */
--c-text-main: #1A1A1A;  /* 主文字色 */
--c-text-sec: #555555;   /* 次要文字色 */
```

#### 字体系统
```css
--f-cn-head: 'NotoSansHans-Medium', sans-serif;  /* 中文标题 */
--f-cn-body: 'NotoSansHans-Regular', sans-serif; /* 中文正文 */
--f-en-head: 'MiSans-Demibold', sans-serif;      /* 英文标题 */
--f-en-body: 'MiSans-Regular', sans-serif;       /* 英文正文 */
```

#### 栅格系统
```css
--grid-cols: 12;
--grid-gap: 24px;
--page-width: 1920px;
--container-width: 1680px;  /* 1920 - 120px * 2 padding */
```

### 2.3 组件识别 [VERIFIED]

基于 HTML 源码分析，识别出以下可复用组件：

#### 布局组件
| 组件名 | 来源 | 复用次数 | 说明 |
|--------|------|----------|------|
| `NoiseTexture` | 首页:318, 文章:622 | 2 | 噪点纹理覆盖层 |
| `GridLines` | 首页:321-325 | 1 | 12 列背景网格线 |
| `Header` | 文章:626-641 | 6 | 文章页固定头部 |
| `Footer` | 首页:532-565, 文章:844-855 | 2 | 两种变体 |

#### 首页组件
| 组件名 | 来源 | 说明 |
|--------|------|------|
| `Hero` | 首页:330-348 | 主视觉区，含动画背景 |
| `ContentSection` | 首页:351-480 | 内容卡片区块，6 个实例 |
| `NetworkJoin` | 首页:483-529 | 加入网络区块，含 SVG 连线 |

#### 文章组件
| 组件名 | 来源 | 说明 |
|--------|------|------|
| `ArticleHero` | 文章:643-650 | 文章标题区 |
| `TableOfContents` | 文章:654-697 | 侧边目录导航 |
| `ArticleContent` | 文章:700-805 | 文章正文区 |
| `RelatedArticles` | 文章:818-842 | 相关阅读 |
| `CTABox` | 文章:796-804 | 行动召唤卡片 |
| `ReadingProgress` | 文章:148-155 | 阅读进度条 |

#### UI 原子组件
| 组件名 | 来源 | 说明 |
|--------|------|------|
| `Button` | 首页:125-161 | 两种变体：primary, outline |
| `ContentCard` | 首页:163-173 | 毛玻璃卡片 |
| `Shape` | 首页:176-192 | 几何图形：circle, square, triangle |
| `LinkArrow` | 首页:64-76 | 箭头链接 |
| `NodeItem` | 首页:253-282 | 网络节点 |
| `QuoteBlock` | 文章:373-392 | 引用块 |
| `Divider` | 文章:394-409 | 分隔符 |

---

## 3. 技术架构

### 3.1 技术栈选型

| 层级 | 技术选型 | 理由 |
|------|----------|------|
| 框架 | Next.js 14 (App Router) | 官方推荐，支持 SSG |
| 语言 | TypeScript | 类型安全，IDE 支持好 |
| 样式 | CSS Modules + CSS Variables | 保留原有 CSS，无学习成本 |
| 图标 | Remix Icon (CDN) | 原 HTML 已使用 |
| 字体 | CDN 加载 | 原 HTML 已使用 |

**为什么不用 Tailwind**：
1. 原 HTML 的 CSS 结构清晰，可直接复用
2. 复杂动画和几何图形用 Tailwind 会很冗长
3. 避免引入额外学习成本

### 3.2 目录结构

```
towow-website/
├── app/                              # Next.js App Router
│   ├── layout.tsx                    # 根布局
│   ├── page.tsx                      # 首页
│   ├── globals.css                   # 全局样式入口
│   └── articles/
│       └── [slug]/
│           └── page.tsx              # 文章详情页
│
├── components/
│   ├── layout/                       # 布局组件
│   │   ├── NoiseTexture.tsx
│   │   ├── NoiseTexture.module.css
│   │   ├── GridLines.tsx
│   │   ├── GridLines.module.css
│   │   ├── Header.tsx
│   │   ├── Header.module.css
│   │   ├── Footer.tsx
│   │   └── Footer.module.css
│   │
│   ├── home/                         # 首页组件
│   │   ├── Hero.tsx
│   │   ├── Hero.module.css
│   │   ├── ContentSection.tsx
│   │   ├── ContentSection.module.css
│   │   ├── NetworkJoin.tsx
│   │   └── NetworkJoin.module.css
│   │
│   ├── article/                      # 文章组件
│   │   ├── ArticleHero.tsx
│   │   ├── ArticleHero.module.css
│   │   ├── TableOfContents.tsx
│   │   ├── TableOfContents.module.css
│   │   ├── ArticleContent.tsx
│   │   ├── ArticleContent.module.css
│   │   ├── RelatedArticles.tsx
│   │   ├── RelatedArticles.module.css
│   │   ├── CTABox.tsx
│   │   └── CTABox.module.css
│   │
│   └── ui/                           # UI 原子组件
│       ├── Button.tsx
│       ├── Button.module.css
│       ├── ContentCard.tsx
│       ├── ContentCard.module.css
│       ├── Shape.tsx
│       ├── Shape.module.css
│       ├── LinkArrow.tsx
│       ├── LinkArrow.module.css
│       ├── NodeItem.tsx
│       ├── NodeItem.module.css
│       ├── QuoteBlock.tsx
│       ├── QuoteBlock.module.css
│       ├── Divider.tsx
│       └── Divider.module.css
│
├── lib/
│   ├── articles.ts                   # 文章数据
│   └── constants.ts                  # 常量定义
│
├── styles/
│   ├── variables.css                 # CSS 变量
│   ├── typography.css                # 排版样式
│   └── animations.css                # 动画关键帧
│
├── public/
│   └── fonts/                        # 本地字体（可选）
│
├── next.config.js
├── tsconfig.json
└── package.json
```

---

## 4. 组件设计与接口契约

### 4.1 布局组件

#### NoiseTexture

```typescript
// components/layout/NoiseTexture.tsx
interface NoiseTextureProps {
  opacity?: number;  // 默认 0.05
}

export function NoiseTexture({ opacity = 0.05 }: NoiseTextureProps): JSX.Element;
```

**样式要点**：
- `position: fixed`
- `z-index: 999`
- `pointer-events: none`
- 使用 SVG filter 生成 fractalNoise

#### GridLines

```typescript
// components/layout/GridLines.tsx
interface GridLinesProps {
  columns?: number;  // 默认 12
}

export function GridLines({ columns = 12 }: GridLinesProps): JSX.Element;
```

**样式要点**：
- `position: fixed`
- `width: 1680px`（container-width）
- 居中对齐
- 每列右边框 `1px solid rgba(0,0,0,0.03)`

#### Header（文章页专用）

```typescript
// components/layout/Header.tsx
interface HeaderProps {
  progress?: number;  // 阅读进度 0-100
}

export function Header({ progress = 0 }: HeaderProps): JSX.Element;
```

**样式要点**：
- `position: fixed`
- `height: 80px`
- `backdrop-filter: blur(10px)`
- 包含：返回按钮、Logo、"加入网络"按钮、进度条

#### Footer

```typescript
// components/layout/Footer.tsx
interface FooterProps {
  variant: 'home' | 'article';
}

export function Footer({ variant }: FooterProps): JSX.Element;
```

**两种变体**：
- `home`: 浅色背景，包含二维码、联系方式、社交链接
- `article`: 深色背景，简洁链接列表

### 4.2 首页组件

#### Hero

```typescript
// components/home/Hero.tsx
interface HeroProps {
  title: React.ReactNode;
  subtitle: string;
  primaryAction: {
    label: string;
    href: string;
  };
  secondaryAction: {
    label: string;
    href: string;
  };
}

export function Hero(props: HeroProps): JSX.Element;
```

**样式要点**：
- `height: 100vh`
- 包含动画背景：`hero-circle`（紫色圆形）、`hero-square`（绿色方形）
- 动画：`growUp` 1.5s ease-out

#### ContentSection

```typescript
// components/home/ContentSection.tsx
interface ContentSectionProps {
  title: string;           // 支持 HTML（用于换行）
  content: string;         // 支持 HTML（用于换行）
  linkText: string;
  linkHref: string;
  gridColumn: string;      // 如 "2 / 7", "7 / 12", "4 / 10"
  children?: React.ReactNode;  // 几何装饰元素
}

export function ContentSection(props: ContentSectionProps): JSX.Element;
```

**样式要点**：
- 使用 `ContentCard` 组件
- `gridColumn` 控制在 12 列网格中的位置
- `children` 用于放置 `Shape` 装饰

#### NetworkJoin

```typescript
// components/home/NetworkJoin.tsx
interface NetworkNode {
  id: string;
  icon: string;           // Remix Icon 类名
  label: string;
  color: string;          // CSS 颜色值
  position: {
    top?: string;
    left?: string;
    right?: string;
  };
  animationDelay?: string;
}

interface NetworkJoinProps {
  nodes: NetworkNode[];
}

export function NetworkJoin({ nodes }: NetworkJoinProps): JSX.Element;
```

**样式要点**：
- 包含 SVG 连接线
- 中心 ToWow 节点
- 5 个浮动节点，各有不同的 `float` 动画延迟

### 4.3 文章组件

#### ArticleHero

```typescript
// components/article/ArticleHero.tsx
interface ArticleHeroProps {
  title: string;
  readingTime: string;    // 如 "12分钟"
  date: string;           // 如 "2026年1月"
}

export function ArticleHero(props: ArticleHeroProps): JSX.Element;
```

**样式要点**：
- `height: 70vh`
- 标题使用 `NotoSerifCJKsc-Bold` 字体
- 包含装饰图片（右上、左下）

#### TableOfContents

```typescript
// components/article/TableOfContents.tsx
interface TOCItem {
  id: string;
  title: string;
}

interface TableOfContentsProps {
  items: TOCItem[];
  activeId?: string;
}

export function TableOfContents(props: TableOfContentsProps): JSX.Element;
```

**样式要点**：
- `position: sticky`
- `top: 120px`
- 包含垂直连接线
- 当前项高亮（紫色圆点）

**交互逻辑**（Client Component）：
- 使用 `IntersectionObserver` 监听章节可见性
- 自动更新 `activeId`

#### ArticleContent

```typescript
// components/article/ArticleContent.tsx
interface ArticleSection {
  id: string;
  title: string;
  content: string;  // HTML 字符串
}

interface ArticleContentProps {
  sections: ArticleSection[];
}

export function ArticleContent({ sections }: ArticleContentProps): JSX.Element;
```

**样式要点**：
- 首字母大写装饰（`first-letter-block`）
- `<strong>` 标签带渐变背景高亮
- 章节间使用 `Divider` 分隔

#### RelatedArticles

```typescript
// components/article/RelatedArticles.tsx
interface RelatedArticle {
  slug: string;
  title: string;
  icon: string;  // Remix Icon 类名
}

interface RelatedArticlesProps {
  articles: RelatedArticle[];
}

export function RelatedArticles({ articles }: RelatedArticlesProps): JSX.Element;
```

#### CTABox

```typescript
// components/article/CTABox.tsx
interface CTABoxProps {
  title: string;
  description: string;
  buttonText: string;
  buttonHref: string;
}

export function CTABox(props: CTABoxProps): JSX.Element;
```

### 4.4 UI 原子组件

#### Button

```typescript
// components/ui/Button.tsx
interface ButtonProps {
  variant: 'primary' | 'outline';
  children: React.ReactNode;
  href?: string;
  onClick?: () => void;
  className?: string;
}

export function Button(props: ButtonProps): JSX.Element;
```

**样式要点**：
- `primary`: 黑底白字，hover 时背景变紫色
- `outline`: 透明底黑边，hover 时背景变紫色
- 使用 `::after` 伪元素实现 hover 动画

#### ContentCard

```typescript
// components/ui/ContentCard.tsx
interface ContentCardProps {
  children: React.ReactNode;
  className?: string;
}

export function ContentCard({ children, className }: ContentCardProps): JSX.Element;
```

**样式要点**：
- `background: rgba(255, 255, 255, 0.5)`
- `backdrop-filter: blur(8px)`
- hover 时 `translateY(-5px)`

#### Shape

```typescript
// components/ui/Shape.tsx
interface ShapeProps {
  type: 'circle' | 'square' | 'triangle';
  size: number;
  color: string;
  position?: {
    top?: string;
    left?: string;
    right?: string;
    bottom?: string;
  };
  animation?: 'float' | 'pulse' | 'spin';
  animationDuration?: string;
  animationDelay?: string;
  opacity?: number;
  blur?: number;
  rotate?: number;
  mixBlendMode?: string;
  border?: string;  // 用于空心图形
}

export function Shape(props: ShapeProps): JSX.Element;
```

**样式要点**：
- `position: absolute`
- `triangle` 使用 border 技巧实现
- 支持 `dither-edge` 效果（mask-image 渐变）

#### LinkArrow

```typescript
// components/ui/LinkArrow.tsx
interface LinkArrowProps {
  href: string;
  children: React.ReactNode;
}

export function LinkArrow({ href, children }: LinkArrowProps): JSX.Element;
```

**样式要点**：
- 包含右箭头图标
- hover 时下划线出现，箭头右移

#### NodeItem

```typescript
// components/ui/NodeItem.tsx
interface NodeItemProps {
  icon: string;
  label: string;
  color: string;
  isSquare?: boolean;  // 默认圆形，可选方形
}

export function NodeItem(props: NodeItemProps): JSX.Element;
```

#### QuoteBlock

```typescript
// components/ui/QuoteBlock.tsx
interface QuoteBlockProps {
  children: React.ReactNode;
}

export function QuoteBlock({ children }: QuoteBlockProps): JSX.Element;
```

**样式要点**：
- 左边框 6px 紫色
- 背景 sage green
- 左上角引号图标

#### Divider

```typescript
// components/ui/Divider.tsx
export function Divider(): JSX.Element;
```

**样式要点**：
- 三个小图形：圆形（紫）、方形（绿）、三角形（杏）
- 居中排列，间距 15px

---

## 5. CSS 变量规范

### 5.1 variables.css

```css
/* styles/variables.css */

:root {
  /* === 颜色系统 === */
  --c-primary: #CBC3E3;      /* Wisteria - 紫藤色 */
  --c-secondary: #D4F4DD;    /* Lime - 青柠色 */
  --c-accent: #FFE4B5;       /* Apricot - 杏色 */
  --c-detail: #E8F3E8;       /* Sage Green - 鼠尾草绿 */
  --c-bg: #EEEEEE;           /* Fog Gray - 雾灰 */
  --c-text-main: #1A1A1A;
  --c-text-sec: #555555;
  --c-text-gray: #666666;
  --c-text-dark: #222222;

  /* === 字体系统 === */
  --f-cn-head: 'NotoSansHans-Medium', sans-serif;
  --f-cn-body: 'NotoSansHans-Regular', sans-serif;
  --f-en-head: 'MiSans-Demibold', sans-serif;
  --f-en-body: 'MiSans-Regular', sans-serif;
  --f-serif: 'NotoSerifCJKsc-Bold', serif;

  /* === 栅格系统 === */
  --grid-cols: 12;
  --grid-gap: 24px;
  --page-width: 1920px;
  --container-width: 1680px;

  /* === 间距系统 === */
  --spacing-xs: 8px;
  --spacing-sm: 16px;
  --spacing-md: 24px;
  --spacing-lg: 32px;
  --spacing-xl: 48px;
  --spacing-2xl: 64px;
  --spacing-3xl: 80px;
  --spacing-section: 240px;

  /* === 圆角 === */
  --radius-sm: 4px;
  --radius-md: 12px;
  --radius-lg: 24px;
  --radius-full: 50px;

  /* === 阴影 === */
  --shadow-sm: 0 5px 15px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 10px 30px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 20px 40px rgba(0, 0, 0, 0.1);

  /* === 过渡 === */
  --transition-fast: 0.2s ease;
  --transition-normal: 0.3s ease;
  --transition-slow: 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);

  /* === Z-Index 层级 === */
  --z-base: 1;
  --z-content: 5;
  --z-header: 100;
  --z-modal: 500;
  --z-noise: 999;
  --z-tooltip: 1000;
}
```

### 5.2 typography.css

```css
/* styles/typography.css */

.text-h1 {
  font-family: var(--f-cn-head);
  font-size: 66px;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: #000;
}

.text-h2 {
  font-family: var(--f-cn-head);
  font-size: 38px;
  line-height: 1.3;
  letter-spacing: -0.01em;
  margin-bottom: var(--spacing-md);
}

.text-h3 {
  font-family: var(--f-cn-head);
  font-size: 32px;
  line-height: 1.3;
}

.text-body {
  font-family: var(--f-cn-body);
  font-size: 19px;
  line-height: 1.75;
  color: var(--c-text-sec);
}

.text-body-lg {
  font-family: var(--f-cn-body);
  font-size: 22px;
  line-height: 1.75;
}

.text-caption {
  font-family: var(--f-cn-body);
  font-size: 14px;
  line-height: 1.5;
  color: var(--c-text-gray);
}

.en-font {
  font-family: var(--f-en-head);
}

/* 文章页特殊排版 */
.article-title {
  font-family: var(--f-serif);
  font-size: 72px;
  line-height: 1.2;
}

.article-body {
  font-family: var(--f-cn-body);
  font-size: 19px;
  line-height: 1.85;
  color: #444;
}

.article-body strong {
  font-weight: 700;
  color: #000;
  background: linear-gradient(
    120deg,
    transparent 0%,
    transparent 60%,
    var(--c-secondary) 60%,
    var(--c-secondary) 90%,
    transparent 90%
  );
}
```

### 5.3 animations.css

```css
/* styles/animations.css */

@keyframes growUp {
  0% {
    transform: translateY(100px) scale(0);
    opacity: 0;
  }
  100% {
    transform: translateY(0) scale(1);
    opacity: 0.6;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.4;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.05);
  }
}

/* 动画工具类 */
.animate-float {
  animation: float 6s ease-in-out infinite;
}

.animate-pulse {
  animation: pulse 6s infinite;
}

.animate-spin {
  animation: spin 60s linear infinite;
}

.animate-grow-up {
  animation: growUp 1.5s ease-out forwards;
}
```

---

## 6. 数据结构

### 6.1 文章数据

```typescript
// lib/articles.ts

export interface ArticleSection {
  id: string;
  title: string;
  content: string;  // HTML 字符串
}

export interface Article {
  slug: string;
  title: string;
  subtitle?: string;
  readingTime: string;
  date: string;
  heroImages?: {
    right?: string;
    left?: string;
  };
  sections: ArticleSection[];
  relatedArticles: string[];  // slugs
}

export const articles: Article[] = [
  {
    slug: 'attention-to-value',
    title: '从注意力到价值：互联网的下一次进化',
    readingTime: '12分钟',
    date: '2026年1月',
    heroImages: {
      right: 'https://a.lovart.ai/artifacts/agent/wvYGTwvJlvD3AVBk.jpg',
      left: 'https://a.lovart.ai/artifacts/agent/1vbMlXkbjNcYRJCe.jpg',
    },
    sections: [
      {
        id: 'section-1',
        title: '认知带宽的限制',
        content: '...',
      },
      // ... 更多章节
    ],
    relatedArticles: ['negotiation-vs-search', 'why-openness', 'individual-as-protagonist'],
  },
  // ... 更多文章
];

export function getArticleBySlug(slug: string): Article | undefined {
  return articles.find(article => article.slug === slug);
}

export function getAllArticleSlugs(): string[] {
  return articles.map(article => article.slug);
}
```

### 6.2 首页数据

```typescript
// lib/constants.ts

export const HOME_SECTIONS = [
  {
    id: 'attention-to-value',
    title: '从注意力到价值：<br>互联网的下一次进化',
    content: '今天的互联网建立在"注意力经济"之上...',
    linkText: '深入阅读：从注意力到价值',
    linkHref: '/articles/attention-to-value',
    gridColumn: '2 / 7',
  },
  // ... 更多区块
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
  // ... 更多节点
];
```

---

## 7. 路由设计

| 路径 | 页面 | 数据来源 |
|------|------|----------|
| `/` | 首页 | `lib/constants.ts` |
| `/articles/attention-to-value` | 从注意力到价值 | `lib/articles.ts` |
| `/articles/negotiation-vs-search` | 协商创造 vs 搜索匹配 | `lib/articles.ts` |
| `/articles/why-openness` | 为什么开放是唯一的选择 | `lib/articles.ts` |
| `/articles/individual-as-protagonist` | 为什么个体才是网络的主角 | `lib/articles.ts` |
| `/articles/agent-explosion` | 端侧Agent的爆发，然后呢 | `lib/articles.ts` |
| `/articles/dao-sheng-yi` | 道生一：极简的技术架构 | `lib/articles.ts` |

---

## 8. 任务依赖分析

### 8.1 依赖关系图

```
Phase 1: 项目初始化
├── TASK-001: 创建 Next.js 项目
│
Phase 2: 基础设施
├── TASK-002: CSS 变量系统 ──────────────────┐
├── TASK-003: 字体配置 ─────────────────────┤
└── TASK-004: 动画系统 ─────────────────────┤
                                             │
Phase 3: UI 组件                             │
├── TASK-005: 布局组件 ◄────────────────────┤
│   ├── NoiseTexture                         │
│   ├── GridLines                            │
│   └── Footer                               │
│                                            │
├── TASK-006: UI 原子组件 ◄─────────────────┘
│   ├── Button
│   ├── Shape
│   ├── ContentCard
│   ├── LinkArrow
│   └── Divider
│
Phase 4: 页面组件
├── TASK-007: 首页组件 ◄──── TASK-005, TASK-006
│   ├── Hero
│   ├── ContentSection
│   └── NetworkJoin
│
├── TASK-008: 文章组件 ◄──── TASK-005, TASK-006
│   ├── Header
│   ├── ArticleHero
│   ├── TableOfContents
│   ├── ArticleContent
│   ├── RelatedArticles
│   └── CTABox
│
Phase 5: 页面集成
├── TASK-009: 首页集成 ◄──── TASK-007
├── TASK-010: 文章页集成 ◄── TASK-008
│
Phase 6: 测试与优化
└── TASK-011: 视觉 QA 与优化 ◄── TASK-009, TASK-010
```

### 8.2 依赖类型说明

| 依赖类型 | 说明 | 处理方式 |
|----------|------|----------|
| **硬依赖** | 代码必须 import 其他任务的模块 | 必须等待完成 |
| **接口依赖** | 只需要约定接口，可并行开发 | 先定义接口契约 |

### 8.3 任务依赖表

| 任务 ID | 任务名称 | 硬依赖 | 接口依赖 | 可并行 |
|---------|----------|--------|----------|--------|
| TASK-001 | 项目初始化 | - | - | - |
| TASK-002 | CSS 变量系统 | TASK-001 | - | 与 003, 004 并行 |
| TASK-003 | 字体配置 | TASK-001 | - | 与 002, 004 并行 |
| TASK-004 | 动画系统 | TASK-001 | - | 与 002, 003 并行 |
| TASK-005 | 布局组件 | TASK-002 | TASK-003, TASK-004 | 与 006 并行 |
| TASK-006 | UI 原子组件 | TASK-002 | TASK-004 | 与 005 并行 |
| TASK-007 | 首页组件 | TASK-005, TASK-006 | - | 与 008 并行 |
| TASK-008 | 文章组件 | TASK-005, TASK-006 | - | 与 007 并行 |
| TASK-009 | 首页集成 | TASK-007 | - | 与 010 并行 |
| TASK-010 | 文章页集成 | TASK-008 | - | 与 009 并行 |
| TASK-011 | 视觉 QA | TASK-009, TASK-010 | - | - |

### 8.4 关键路径

```
TASK-001 → TASK-002 → TASK-005 → TASK-007 → TASK-009 → TASK-011
                    ↘ TASK-006 ↗         ↘ TASK-008 → TASK-010 ↗
```

**关键路径时长**: 约 5 天（假设每个任务 1 天）

**并行优化**:
- Phase 2 的三个任务可完全并行
- Phase 3 的两个任务可完全并行
- Phase 4 的两个任务可完全并行
- Phase 5 的两个任务可完全并行

**优化后时长**: 约 3 天

---

## 9. 实现步骤

### Phase 1: 项目初始化 (Day 1 上午)

1. 创建 Next.js 项目
2. 配置 TypeScript
3. 创建目录结构
4. 配置 CSS Modules

### Phase 2: 基础设施 (Day 1 下午)

1. 创建 CSS 变量文件
2. 配置字体加载
3. 创建动画关键帧

### Phase 3: UI 组件 (Day 2)

1. 实现布局组件
2. 实现 UI 原子组件
3. 组件单元测试

### Phase 4: 页面组件 (Day 3)

1. 实现首页组件
2. 实现文章组件
3. 组件集成测试

### Phase 5: 页面集成 (Day 4)

1. 集成首页
2. 集成文章页
3. 创建文章数据

### Phase 6: 测试与优化 (Day 5)

1. 视觉 QA（与原 HTML 对比）
2. 性能优化
3. 代码清理

---

## 10. 风险与预案

| 风险 | 影响 | 概率 | 预案 |
|------|------|------|------|
| 字体加载失败 | 视觉不一致 | 低 | 配置 fallback 字体 |
| CSS 变量浏览器兼容 | 样式异常 | 低 | 使用 PostCSS 编译 |
| 动画性能问题 | 页面卡顿 | 中 | 使用 `will-change` 优化 |
| 图片加载慢 | 首屏体验差 | 中 | 使用 Next.js Image 优化 |

---

## 11. 未决项

| 编号 | 问题 | 状态 | 负责人 |
|------|------|------|--------|
| [OPEN-1] | 是否需要响应式设计？ | 待决策 | - |
| [OPEN-2] | 文章内容是否需要 MDX 支持？ | 待决策 | - |
| [OPEN-3] | 是否需要 SEO 优化（meta tags）？ | 待决策 | - |
| [TBD-1] | 部署平台选择（Vercel/其他） | 待决策 | - |

---

## 附录 A: 代码引用

| 文件 | 行号 | 内容 |
|------|------|------|
| `ToWow - 几何花园 V1.html` | 19-40 | CSS 变量定义 |
| `ToWow - 几何花园 V1.html` | 125-161 | Button 样式 |
| `ToWow - 几何花园 V1.html` | 163-173 | ContentCard 样式 |
| `ToWow - 几何花园 V1.html` | 176-192 | Shape 样式 |
| `ToWow - 几何花园 V1.html` | 294-309 | 动画关键帧 |
| `从注意力到价值 - ToWow深度阅读.html` | 98-156 | Header 样式 |
| `从注意力到价值 - ToWow深度阅读.html` | 229-308 | TOC 样式 |
| `从注意力到价值 - ToWow深度阅读.html` | 310-409 | Article 样式 |
