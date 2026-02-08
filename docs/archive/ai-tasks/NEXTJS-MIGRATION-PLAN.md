# ToWow HTML to Next.js Migration Plan

## Overview

将现有的 ToWow 静态 HTML 页面迁移到 Next.js 项目，保持原有视觉设计不变，同时实现组件化和模块化。

---

## 1. Project Structure

```
towow-website/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout (fonts, noise texture, grid lines)
│   ├── page.tsx                  # Homepage (几何花园)
│   ├── globals.css               # Global styles & CSS variables
│   └── articles/
│       └── [slug]/
│           └── page.tsx          # Article detail page
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx            # Site header (article pages)
│   │   ├── Footer.tsx            # Site footer
│   │   ├── NoiseTexture.tsx      # Noise overlay effect
│   │   └── GridLines.tsx         # Background grid lines
│   │
│   ├── home/
│   │   ├── Hero.tsx              # Hero section with animated shapes
│   │   ├── ContentSection.tsx    # Reusable content card section
│   │   ├── NetworkJoin.tsx       # Join network section with nodes
│   │   └── SectionVisual.tsx     # Geometric decorations wrapper
│   │
│   ├── article/
│   │   ├── ArticleHero.tsx       # Article hero with title & meta
│   │   ├── ArticleContent.tsx    # Main article body
│   │   ├── TableOfContents.tsx   # Sticky sidebar TOC
│   │   ├── RelatedArticles.tsx   # Related reading section
│   │   ├── CTABox.tsx            # Call-to-action box
│   │   └── ReadingProgress.tsx   # Progress bar in header
│   │
│   └── ui/
│       ├── Button.tsx            # btn-primary, btn-outline
│       ├── ContentCard.tsx       # Glass morphism card
│       ├── LinkArrow.tsx         # Arrow link component
│       ├── Shape.tsx             # Geometric shape (circle, square, triangle)
│       ├── NodeItem.tsx          # Network node with icon
│       ├── QuoteBlock.tsx        # Styled quote block
│       └── Divider.tsx           # Section divider with shapes
│
├── lib/
│   ├── articles.ts               # Article data & utilities
│   └── constants.ts              # Site-wide constants
│
├── styles/
│   ├── variables.css             # CSS custom properties
│   ├── typography.css            # Typography classes
│   ├── animations.css            # Keyframe animations
│   └── components/               # Component-specific styles (if needed)
│
├── public/
│   └── fonts/                    # Local font files (optional)
│
├── next.config.js
├── tailwind.config.ts            # (Optional, see styling section)
├── tsconfig.json
└── package.json
```

---

## 2. Component Breakdown

### 2.1 Layout Components

#### `NoiseTexture.tsx`
```tsx
// Fixed position noise overlay
// Uses SVG filter for fractal noise
// z-index: 999, pointer-events: none
```

#### `GridLines.tsx`
```tsx
// 12-column background grid
// Fixed position, centered
// 1680px width with 24px gaps
```

#### `Header.tsx` (Article pages only)
```tsx
// Fixed header with:
// - Back button + Logo
// - "加入网络" button
// - Reading progress bar
```

#### `Footer.tsx`
```tsx
// Two variants:
// 1. Homepage: Light background, QR code, contact info
// 2. Article: Dark background, simple links
```

### 2.2 Homepage Components

#### `Hero.tsx`
```tsx
interface HeroProps {
  title: React.ReactNode;
  subtitle: string;
  primaryAction: { label: string; href: string };
  secondaryAction: { label: string; href: string };
}
// Includes animated circle and square backgrounds
```

#### `ContentSection.tsx`
```tsx
interface ContentSectionProps {
  title: string;
  content: string;
  linkText: string;
  linkHref: string;
  position: 'left' | 'right' | 'center';  // Grid column position
  visualElements?: React.ReactNode;        // Geometric decorations
}
// Reusable for all 6 content sections
```

#### `NetworkJoin.tsx`
```tsx
// Special section with:
// - SVG connecting lines
// - Central ToWow node
// - 5 floating role nodes (黑客松, AI社区, etc.)
```

### 2.3 Article Components

#### `ArticleHero.tsx`
```tsx
interface ArticleHeroProps {
  title: string;
  readingTime: string;
  date: string;
}
// Includes decorative images
```

#### `TableOfContents.tsx`
```tsx
interface TOCItem {
  id: string;
  title: string;
}
interface TableOfContentsProps {
  items: TOCItem[];
  activeId?: string;
}
// Sticky sidebar with scroll tracking
```

#### `ArticleContent.tsx`
```tsx
// Renders article body with:
// - First letter styling
// - Quote blocks
// - Section dividers
// - Highlighted text (strong with gradient)
```

### 2.4 UI Components

#### `Button.tsx`
```tsx
interface ButtonProps {
  variant: 'primary' | 'outline';
  children: React.ReactNode;
  href?: string;
  onClick?: () => void;
}
// Hover effect with ::after pseudo-element
```

#### `ContentCard.tsx`
```tsx
// Glass morphism card
// backdrop-filter: blur(8px)
// Hover: translateY(-5px)
```

#### `Shape.tsx`
```tsx
interface ShapeProps {
  type: 'circle' | 'square' | 'triangle';
  size: number;
  color: string;
  style?: React.CSSProperties;
  animate?: 'float' | 'pulse' | 'spin';
  dither?: boolean;
}
```

---

## 3. Styling Strategy

### Recommendation: CSS Modules + CSS Variables

**Why CSS Modules:**
1. **Preserves existing CSS** - Can directly copy existing styles with minimal changes
2. **No learning curve** - Standard CSS syntax
3. **Scoped by default** - No class name conflicts
4. **Easy migration** - HTML styles can be extracted directly

**Why NOT Tailwind:**
1. Complex custom animations would require extensive config
2. Geometric shapes with specific pixel values are verbose in Tailwind
3. Existing CSS is well-structured and can be reused

### CSS Structure

```
styles/
├── variables.css          # CSS custom properties (colors, fonts, grid)
├── globals.css            # Reset, base styles, utility classes
├── typography.css         # .text-h1, .text-h2, .text-body, etc.
├── animations.css         # @keyframes float, pulse, spin, growUp
└── components/
    ├── Button.module.css
    ├── ContentCard.module.css
    ├── Shape.module.css
    └── ...
```

### CSS Variables (from existing HTML)

```css
:root {
  /* Colors */
  --c-primary: #CBC3E3;    /* Wisteria */
  --c-secondary: #D4F4DD;  /* Lime */
  --c-accent: #FFE4B5;     /* Apricot */
  --c-detail: #E8F3E8;     /* Sage Green */
  --c-bg: #EEEEEE;         /* Fog Gray */
  --c-text-main: #1A1A1A;
  --c-text-sec: #555555;

  /* Typography */
  --f-cn-head: 'NotoSansHans-Medium', sans-serif;
  --f-cn-body: 'NotoSansHans-Regular', sans-serif;
  --f-en-head: 'MiSans-Demibold', sans-serif;
  --f-en-body: 'MiSans-Regular', sans-serif;

  /* Grid */
  --grid-cols: 12;
  --grid-gap: 24px;
  --page-width: 1920px;
  --container-width: 1680px;
}
```

---

## 4. Routing Design

### Routes

| Path | Page | Description |
|------|------|-------------|
| `/` | Homepage | 几何花园首页 |
| `/articles/attention-to-value` | Article | 从注意力到价值 |
| `/articles/negotiation-vs-search` | Article | 协商创造 vs 搜索匹配 |
| `/articles/why-openness` | Article | 为什么开放是唯一的选择 |
| `/articles/individual-as-protagonist` | Article | 为什么个体才是网络的主角 |
| `/articles/agent-explosion` | Article | 端侧Agent的爆发，然后呢 |
| `/articles/dao-sheng-yi` | Article | 道生一：极简的技术架构 |

### Article Data Structure

```typescript
// lib/articles.ts
interface Article {
  slug: string;
  title: string;
  subtitle?: string;
  readingTime: string;
  date: string;
  sections: {
    id: string;
    title: string;
    content: string;  // HTML string or MDX
  }[];
  relatedArticles: string[];  // slugs
}

const articles: Article[] = [
  {
    slug: 'attention-to-value',
    title: '从注意力到价值：互联网的下一次进化',
    readingTime: '12分钟',
    date: '2026年1月',
    sections: [
      { id: 'section-1', title: '认知带宽的限制', content: '...' },
      { id: 'section-2', title: '注意力经济的诞生', content: '...' },
      // ...
    ],
    relatedArticles: ['negotiation-vs-search', 'why-openness', 'individual-as-protagonist']
  },
  // ...
];
```

---

## 5. Implementation Steps

### Phase 1: Project Setup (Day 1)

1. **Initialize Next.js project**
   ```bash
   npx create-next-app@latest towow-website --typescript --app --src-dir=false
   ```

2. **Configure fonts**
   - Download fonts or use CDN URLs
   - Set up `@font-face` in globals.css

3. **Set up CSS structure**
   - Create `styles/` directory
   - Extract CSS variables from HTML
   - Create animation keyframes

4. **Create base layout**
   - `app/layout.tsx` with NoiseTexture and GridLines
   - Set up 1920px fixed width

### Phase 2: UI Components (Day 2)

1. **Build atomic components**
   - `Button.tsx`
   - `Shape.tsx`
   - `ContentCard.tsx`
   - `LinkArrow.tsx`

2. **Test components in isolation**
   - Verify hover effects
   - Verify animations

### Phase 3: Homepage (Day 3)

1. **Build homepage sections**
   - `Hero.tsx` with animations
   - `ContentSection.tsx` (reusable)
   - `NetworkJoin.tsx`
   - `Footer.tsx` (homepage variant)

2. **Assemble homepage**
   - `app/page.tsx`
   - Add all 7 sections
   - Verify visual match with original

### Phase 4: Article Pages (Day 4)

1. **Build article components**
   - `Header.tsx` with progress bar
   - `ArticleHero.tsx`
   - `TableOfContents.tsx`
   - `ArticleContent.tsx`
   - `RelatedArticles.tsx`
   - `CTABox.tsx`

2. **Create article data**
   - Extract content from HTML files
   - Structure in `lib/articles.ts`

3. **Build dynamic route**
   - `app/articles/[slug]/page.tsx`
   - `generateStaticParams()` for SSG

### Phase 5: Polish & Testing (Day 5)

1. **Visual QA**
   - Compare with original HTML side-by-side
   - Fix any discrepancies

2. **Add interactions**
   - TOC scroll tracking
   - Reading progress bar
   - Smooth scroll to sections

3. **Performance optimization**
   - Image optimization
   - Font loading strategy

---

## 6. Key Implementation Notes

### 6.1 Fixed Width Handling

```tsx
// app/layout.tsx
export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      <body style={{ width: '1920px', margin: '0 auto' }}>
        <NoiseTexture />
        <GridLines />
        {children}
      </body>
    </html>
  );
}
```

### 6.2 Geometric Shapes Pattern

```tsx
// components/ui/Shape.tsx
interface ShapeProps {
  type: 'circle' | 'square' | 'triangle';
  size: number;
  color: string;
  position: { top?: string; left?: string; right?: string; bottom?: string };
  animation?: 'float' | 'pulse' | 'spin';
  opacity?: number;
  blur?: number;
  rotate?: number;
}

export function Shape({ type, size, color, position, animation, opacity = 1, blur, rotate }: ShapeProps) {
  const baseStyle: React.CSSProperties = {
    position: 'absolute',
    width: size,
    height: size,
    backgroundColor: type !== 'triangle' ? color : 'transparent',
    opacity,
    ...position,
    filter: blur ? `blur(${blur}px)` : undefined,
    transform: rotate ? `rotate(${rotate}deg)` : undefined,
  };

  // Handle triangle with border trick
  if (type === 'triangle') {
    return (
      <div style={{
        ...baseStyle,
        width: 0,
        height: 0,
        borderLeft: `${size/2}px solid transparent`,
        borderRight: `${size/2}px solid transparent`,
        borderBottom: `${size * 0.866}px solid ${color}`,
      }} />
    );
  }

  return (
    <div
      style={baseStyle}
      className={cn(
        type === 'circle' && styles.circle,
        animation && styles[animation]
      )}
    />
  );
}
```

### 6.3 Content Section Pattern

```tsx
// components/home/ContentSection.tsx
interface ContentSectionProps {
  title: string;
  content: string;
  linkText: string;
  linkHref: string;
  gridColumn: string;  // e.g., "2 / 7", "7 / 12", "4 / 10"
  children?: React.ReactNode;  // Visual decorations
}

export function ContentSection({ title, content, linkText, linkHref, gridColumn, children }: ContentSectionProps) {
  return (
    <section className={styles.section}>
      {children}  {/* Geometric decorations */}
      <div className={styles.gridWrapper}>
        <div style={{ gridColumn }} className={styles.contentCard}>
          <h2 className={styles.title} dangerouslySetInnerHTML={{ __html: title }} />
          <p className={styles.body} dangerouslySetInnerHTML={{ __html: content }} />
          <LinkArrow href={linkHref}>{linkText}</LinkArrow>
        </div>
      </div>
    </section>
  );
}
```

### 6.4 Article TOC with Scroll Tracking

```tsx
// components/article/TableOfContents.tsx
'use client';

import { useEffect, useState } from 'react';

export function TableOfContents({ items }: { items: TOCItem[] }) {
  const [activeId, setActiveId] = useState(items[0]?.id);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      { rootMargin: '-80px 0px -80% 0px' }
    );

    items.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [items]);

  return (
    <nav className={styles.toc}>
      {/* ... */}
    </nav>
  );
}
```

---

## 7. File Mapping

| Original HTML | Next.js Location |
|---------------|------------------|
| `ToWow - 几何花园 V1.html` | `app/page.tsx` |
| `从注意力到价值 - ToWow深度阅读.html` | `app/articles/attention-to-value/page.tsx` |
| `协商创造 vs 搜索匹配 - ToWow深度阅读.html` | `app/articles/negotiation-vs-search/page.tsx` |
| `为什么开放是唯一的选择 - ToWow深度阅读.html` | `app/articles/why-openness/page.tsx` |
| `为什么个体才是网络的主角 - ToWow深度阅读.html` | `app/articles/individual-as-protagonist/page.tsx` |
| `端侧Agent的爆发，然后呢 - ToWow深度阅读.html` | `app/articles/agent-explosion/page.tsx` |
| `道生一：极简的技术架构 - ToWow深度阅读.html` | `app/articles/dao-sheng-yi/page.tsx` |

---

## 8. Dependencies

```json
{
  "dependencies": {
    "next": "^14.x",
    "react": "^18.x",
    "react-dom": "^18.x"
  },
  "devDependencies": {
    "typescript": "^5.x",
    "@types/node": "^20.x",
    "@types/react": "^18.x",
    "@types/react-dom": "^18.x"
  }
}
```

**No additional UI libraries needed** - the design is custom and can be implemented with pure CSS.

---

## 9. Summary

| Aspect | Decision |
|--------|----------|
| Framework | Next.js 14 with App Router |
| Language | TypeScript |
| Styling | CSS Modules + CSS Variables |
| Routing | Dynamic routes for articles |
| Data | Static article data in TypeScript |
| Fonts | CDN (existing URLs) or local |
| Icons | Remix Icon (CDN) |

This plan prioritizes:
1. **Fidelity** - Exact visual match with original HTML
2. **Simplicity** - No unnecessary abstractions
3. **Maintainability** - Clear component boundaries
4. **Performance** - Static generation where possible
