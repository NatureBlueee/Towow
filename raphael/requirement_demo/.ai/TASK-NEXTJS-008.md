# TASK-NEXTJS-008: 文章组件

## 任务元信息

- **任务 ID**: TASK-NEXTJS-008
- **Beads ID**: `towow-4us`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 5 小时
- **状态**: TODO

---

## 1. 目标

实现文章页专用组件，包括 ArticleHero、TableOfContents、ArticleContent、RelatedArticles、CTABox。

---

## 2. 输入

- `从注意力到价值 - ToWow深度阅读.html` 第 157-216 行（ArticleHero）
- `从注意力到价值 - ToWow深度阅读.html` 第 229-308 行（TableOfContents）
- `从注意力到价值 - ToWow深度阅读.html` 第 310-409 行（ArticleContent 样式）
- `从注意力到价值 - ToWow深度阅读.html` 第 411-462 行（CTABox）
- `从注意力到价值 - ToWow深度阅读.html` 第 515-573 行（RelatedArticles）
- TECH-NEXTJS-MIGRATION-v5.md 第 4.3 节的接口契约

---

## 3. 输出

- `components/article/ArticleHero.tsx` + `.module.css`
- `components/article/TableOfContents.tsx` + `.module.css`
- `components/article/ArticleContent.tsx` + `.module.css`
- `components/article/RelatedArticles.tsx` + `.module.css`
- `components/article/CTABox.tsx` + `.module.css`

---

## 4. 验收标准

### 4.1 ArticleHero 验收

- [ ] 高度 70vh
- [ ] 标题使用衬线字体 72px
- [ ] 阅读时长和日期显示正确
- [ ] 装饰图片位置正确（右上、左下）
- [ ] 背景几何图形正确

### 4.2 TableOfContents 验收

- [ ] 固定定位 `position: sticky`
- [ ] 垂直连接线显示
- [ ] 当前章节高亮（紫色圆点）
- [ ] 滚动时自动更新高亮
- [ ] 点击跳转到对应章节

### 4.3 ArticleContent 验收

- [ ] 首字母大写装饰
- [ ] `<strong>` 标签渐变背景高亮
- [ ] 章节标题左侧装饰方块
- [ ] 章节间 Divider 分隔
- [ ] QuoteBlock 样式正确

### 4.4 RelatedArticles 验收

- [ ] 卡片列表布局
- [ ] 图标 + 标题
- [ ] hover 效果

### 4.5 CTABox 验收

- [ ] 渐变背景
- [ ] 标题 + 描述 + 按钮
- [ ] 装饰图形

---

## 5. 实现步骤

### 5.1 ArticleHero 组件

```typescript
// components/article/ArticleHero.tsx
import styles from './ArticleHero.module.css';

interface ArticleHeroProps {
  title: string;
  readingTime: string;
  date: string;
  heroImages?: {
    right?: string;
    left?: string;
  };
}

export function ArticleHero({
  title,
  readingTime,
  date,
  heroImages,
}: ArticleHeroProps) {
  return (
    <section className={styles.hero}>
      {/* 装饰图片 */}
      {heroImages?.right && (
        <div
          className={styles.decorRight}
          style={{ backgroundImage: `url(${heroImages.right})` }}
        />
      )}
      {heroImages?.left && (
        <div
          className={styles.decorLeft}
          style={{ backgroundImage: `url(${heroImages.left})` }}
        />
      )}

      {/* 标题 */}
      <h1
        className={styles.title}
        dangerouslySetInnerHTML={{ __html: title.replace('：', '：<br>') }}
      />

      {/* 元信息 */}
      <div className={styles.meta}>
        <i className="ri-time-line" />
        阅读时长 {readingTime} · {date}
      </div>
    </section>
  );
}
```

### 5.2 TableOfContents 组件（Client Component）

```typescript
// components/article/TableOfContents.tsx
'use client';

import { useEffect, useState } from 'react';
import styles from './TableOfContents.module.css';

interface TOCItem {
  id: string;
  title: string;
}

interface TableOfContentsProps {
  items: TOCItem[];
}

export function TableOfContents({ items }: TableOfContentsProps) {
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

  const handleClick = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <nav className={styles.toc}>
      <div className={styles.title}>
        <i className="ri-list-check-2" /> 目录
      </div>
      <ul className={styles.list}>
        <div className={styles.line} />
        {items.map((item) => (
          <li
            key={item.id}
            className={`${styles.item} ${activeId === item.id ? styles.active : ''}`}
          >
            <button
              className={styles.link}
              onClick={() => handleClick(item.id)}
            >
              <div className={styles.marker} />
              <span>{item.title}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
```

### 5.3 ArticleContent 组件

```typescript
// components/article/ArticleContent.tsx
import { QuoteBlock } from '@/components/ui/QuoteBlock';
import { Divider } from '@/components/ui/Divider';
import styles from './ArticleContent.module.css';

interface ArticleSection {
  id: string;
  title: string;
  content: string;
}

interface ArticleContentProps {
  sections: ArticleSection[];
}

export function ArticleContent({ sections }: ArticleContentProps) {
  return (
    <article className={styles.article}>
      {sections.map((section, index) => (
        <div key={section.id}>
          <div id={section.id}>
            <h2 className={styles.sectionTitle}>{section.title}</h2>
            <div
              className={styles.sectionContent}
              dangerouslySetInnerHTML={{ __html: section.content }}
            />
          </div>
          {index < sections.length - 1 && <Divider />}
        </div>
      ))}
    </article>
  );
}
```

### 5.4 RelatedArticles 组件

```typescript
// components/article/RelatedArticles.tsx
import Link from 'next/link';
import styles from './RelatedArticles.module.css';

interface RelatedArticle {
  slug: string;
  title: string;
  icon: string;
}

interface RelatedArticlesProps {
  articles: RelatedArticle[];
}

export function RelatedArticles({ articles }: RelatedArticlesProps) {
  return (
    <section className={styles.section}>
      <div className={styles.container}>
        <h4 className={styles.title}>延伸阅读</h4>
        <div className={styles.list}>
          {articles.map((article) => (
            <Link
              key={article.slug}
              href={`/articles/${article.slug}`}
              className={styles.card}
            >
              <div className={styles.icon}>
                <i className={article.icon} />
              </div>
              <div className={styles.text}>{article.title}</div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
```

### 5.5 CTABox 组件

```typescript
// components/article/CTABox.tsx
import { Button } from '@/components/ui/Button';
import styles from './CTABox.module.css';

interface CTABoxProps {
  title: string;
  description: string;
  buttonText: string;
  buttonHref: string;
}

export function CTABox({
  title,
  description,
  buttonText,
  buttonHref,
}: CTABoxProps) {
  return (
    <div className={styles.box}>
      <div className={styles.decor} />
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.desc}>{description}</p>
      <Button variant="primary" href={buttonHref}>
        <span>{buttonText}</span>
        <i className="ri-arrow-right-line" />
      </Button>
    </div>
  );
}
```

---

## 6. 依赖关系

### 6.1 硬依赖

- TASK-NEXTJS-005: 布局组件（Header）
- TASK-NEXTJS-006: UI 原子组件（Button, QuoteBlock, Divider）

### 6.2 接口依赖

无

### 6.3 被依赖

- TASK-NEXTJS-010: 文章页集成

---

## 7. 技术说明

### 7.1 组件类型

| 组件 | 类型 | 原因 |
|------|------|------|
| ArticleHero | Server | 纯展示 |
| TableOfContents | **Client** | 需要 IntersectionObserver |
| ArticleContent | Server | 纯展示 |
| RelatedArticles | Server | 纯展示 |
| CTABox | Server | 纯展示 |

### 7.2 IntersectionObserver 配置

```javascript
{ rootMargin: '-80px 0px -80% 0px' }
```

- `-80px` 顶部：考虑固定 Header 高度
- `-80%` 底部：章节进入视口 20% 时触发

### 7.3 首字母装饰实现

```css
.firstLetter {
  float: left;
  font-size: 64px;
  line-height: 1;
  padding: 10px 20px 10px 0;
  font-family: var(--f-serif);
  position: relative;
}

.firstLetterBg {
  position: absolute;
  top: 15px;
  left: -10px;
  width: 50px;
  height: 50px;
  background-color: var(--c-detail);
  border-radius: 50%;
  z-index: -1;
}
```

---

## 8. 注意事项

- TableOfContents 是 Client Component，注意 'use client' 指令
- ArticleContent 的 HTML 内容需要正确处理 QuoteBlock
- 首字母装饰只应用于第一个章节的第一段
- 测试时注意滚动监听的性能
