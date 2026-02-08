# TASK-NEXTJS-010: 文章页集成

## 任务元信息

- **任务 ID**: TASK-NEXTJS-010
- **Beads ID**: `towow-agu`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 4 小时
- **状态**: TODO

---

## 1. 目标

将所有文章组件集成到 `app/articles/[slug]/page.tsx`，完成文章页的完整实现，并创建所有文章数据。

---

## 2. 输入

- `从注意力到价值 - ToWow深度阅读.html` 完整文件
- 其他 5 篇文章 HTML 文件
- TASK-NEXTJS-008 产出的文章组件
- TECH-NEXTJS-MIGRATION-v5.md 第 6.1 节的文章数据结构

---

## 3. 输出

- `app/articles/[slug]/page.tsx` - 文章详情页
- `lib/articles.ts` - 文章数据（6 篇文章）

---

## 4. 验收标准

### 4.1 页面结构验收

- [ ] Header（含阅读进度条）
- [ ] ArticleHero
- [ ] 三栏布局：TOC | Content | Decorations
- [ ] CTABox
- [ ] RelatedArticles
- [ ] Footer（article 变体）

### 4.2 功能验收

- [ ] 动态路由正常工作
- [ ] 6 篇文章都可访问
- [ ] TOC 滚动高亮正常
- [ ] TOC 点击跳转正常
- [ ] 阅读进度条正常更新

### 4.3 视觉验收

- [ ] 与原 HTML 视觉效果 100% 一致
- [ ] 首字母装饰正确
- [ ] 引用块样式正确
- [ ] 分隔符样式正确

### 4.4 数据验收

- [ ] 6 篇文章内容完整
- [ ] 相关文章链接正确
- [ ] 阅读时长正确

---

## 5. 实现步骤

### 5.1 创建 lib/articles.ts

```typescript
// lib/articles.ts

export interface ArticleSection {
  id: string;
  title: string;
  content: string;
}

export interface Article {
  slug: string;
  title: string;
  readingTime: string;
  date: string;
  heroImages?: {
    right?: string;
    left?: string;
  };
  sections: ArticleSection[];
  relatedArticles: {
    slug: string;
    title: string;
    icon: string;
  }[];
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
        content: `<p>
          <span class="first-letter-block">
            <span class="first-letter-bg"></span>
            互
          </span>
          联网解决了一个根本性的问题：让信息可以被任何需要它的人找到...
        </p>`,
      },
      {
        id: 'section-2',
        title: '注意力经济的诞生',
        content: `<p>于是"注意力"成了最稀缺的资源...</p>`,
      },
      // ... 更多章节
    ],
    relatedArticles: [
      {
        slug: 'negotiation-vs-search',
        title: '协商创造 vs 搜索匹配：互联网底层范式的迁移',
        icon: 'ri-shake-hands-line',
      },
      {
        slug: 'why-openness',
        title: '为什么开放是唯一的选择：封闭系统的终结',
        icon: 'ri-global-line',
      },
      {
        slug: 'individual-as-protagonist',
        title: '为什么个体才是网络的主角：去中心化的必然',
        icon: 'ri-user-star-line',
      },
    ],
  },
  // ... 其他 5 篇文章
];

export function getArticleBySlug(slug: string): Article | undefined {
  return articles.find((article) => article.slug === slug);
}

export function getAllArticleSlugs(): string[] {
  return articles.map((article) => article.slug);
}
```

### 5.2 创建 app/articles/[slug]/page.tsx

```typescript
// app/articles/[slug]/page.tsx
import { notFound } from 'next/navigation';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { ArticleHero } from '@/components/article/ArticleHero';
import { TableOfContents } from '@/components/article/TableOfContents';
import { ArticleContent } from '@/components/article/ArticleContent';
import { CTABox } from '@/components/article/CTABox';
import { RelatedArticles } from '@/components/article/RelatedArticles';
import { getArticleBySlug, getAllArticleSlugs } from '@/lib/articles';
import styles from './page.module.css';

interface PageProps {
  params: {
    slug: string;
  };
}

// 静态生成所有文章页面
export function generateStaticParams() {
  return getAllArticleSlugs().map((slug) => ({ slug }));
}

export default function ArticlePage({ params }: PageProps) {
  const article = getArticleBySlug(params.slug);

  if (!article) {
    notFound();
  }

  const tocItems = article.sections.map((section) => ({
    id: section.id,
    title: section.title,
  }));

  return (
    <>
      <Header />

      <ArticleHero
        title={article.title}
        readingTime={article.readingTime}
        date={article.date}
        heroImages={article.heroImages}
      />

      <div className={styles.container}>
        {/* 左侧 TOC */}
        <aside className={styles.sidebar}>
          <TableOfContents items={tocItems} />
        </aside>

        {/* 中间内容 */}
        <main className={styles.main}>
          <ArticleContent sections={article.sections} />

          <CTABox
            title="准备好加入价值网络了吗？"
            description="ToWow正在构建Agent时代的开放协作网络，让价值自由流动。"
            buttonText="加入我们"
            buttonHref="#"
          />
        </main>

        {/* 右侧装饰 */}
        <aside className={styles.rightDecor}>
          {/* 视差装饰图形 */}
        </aside>
      </div>

      <RelatedArticles articles={article.relatedArticles} />

      <Footer variant="article" />
    </>
  );
}
```

### 5.3 创建页面样式

```css
/* app/articles/[slug]/page.module.css */
.container {
  display: grid;
  grid-template-columns: 1fr 720px 1fr;
  gap: 40px;
  max-width: 1440px;
  margin: 0 auto;
  position: relative;
  padding-bottom: 120px;
}

.sidebar {
  padding-top: 40px;
}

.main {
  padding-top: 40px;
}

.rightDecor {
  padding-top: 200px;
  position: relative;
}
```

### 5.4 提取文章内容

从 6 个 HTML 文件中提取文章内容，填充到 `lib/articles.ts`。

---

## 6. 依赖关系

### 6.1 硬依赖

- TASK-NEXTJS-008: 文章组件

### 6.2 接口依赖

无

### 6.3 被依赖

- TASK-NEXTJS-011: 视觉 QA

---

## 7. 技术说明

### 7.1 静态生成 (SSG)

使用 `generateStaticParams` 在构建时生成所有文章页面：

```typescript
export function generateStaticParams() {
  return getAllArticleSlugs().map((slug) => ({ slug }));
}
```

### 7.2 阅读进度条实现

需要在页面级别监听滚动事件，计算进度并传递给 Header：

```typescript
// 需要创建一个 Client Component 包装器
'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/Header';

export function ArticlePageClient({ children }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = (scrollTop / docHeight) * 100;
      setProgress(Math.min(100, Math.max(0, progress)));
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <>
      <Header progress={progress} />
      {children}
    </>
  );
}
```

### 7.3 文章内容处理

文章内容包含 HTML 标签，需要注意：
- 首字母装饰需要特殊处理
- QuoteBlock 需要识别并渲染为组件
- `<strong>` 标签的渐变背景通过 CSS 实现

---

## 8. 注意事项

- 文章内容较多，注意代码组织
- 确保所有文章的 slug 与路由匹配
- 测试 404 页面（访问不存在的 slug）
- 测试阅读进度条的准确性
- 测试 TOC 滚动高亮的准确性
