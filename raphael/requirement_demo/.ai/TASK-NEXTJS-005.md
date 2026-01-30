# TASK-NEXTJS-005: 布局组件

## 任务元信息

- **任务 ID**: TASK-NEXTJS-005
- **Beads ID**: `towow-dxw`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 3 小时
- **状态**: TODO

---

## 1. 目标

实现所有布局组件，包括 NoiseTexture、GridLines、Header 和 Footer。

---

## 2. 输入

- `ToWow - 几何花园 V1.html` 第 96-122 行（GridLines, NoiseTexture）
- `ToWow - 几何花园 V1.html` 第 284-291 行（Footer - home 变体）
- `从注意力到价值 - ToWow深度阅读.html` 第 98-156 行（Header）
- `从注意力到价值 - ToWow深度阅读.html` 第 575-617 行（Footer - article 变体）
- TECH-NEXTJS-MIGRATION-v5.md 第 4.1 节的接口契约

---

## 3. 输出

- `components/layout/NoiseTexture.tsx` + `.module.css`
- `components/layout/GridLines.tsx` + `.module.css`
- `components/layout/Header.tsx` + `.module.css`
- `components/layout/Footer.tsx` + `.module.css`

---

## 4. 验收标准

### 4.1 NoiseTexture 验收

- [ ] 覆盖整个视口
- [ ] `z-index: 999`
- [ ] `pointer-events: none`
- [ ] 噪点效果与原 HTML 一致
- [ ] 支持 `opacity` 属性

### 4.2 GridLines 验收

- [ ] 12 列网格线
- [ ] 宽度 1680px，居中
- [ ] 固定定位
- [ ] 线条颜色 `rgba(0,0,0,0.03)`

### 4.3 Header 验收（文章页）

- [ ] 固定定位，高度 80px
- [ ] 毛玻璃效果 `backdrop-filter: blur(10px)`
- [ ] 包含返回按钮、Logo、"加入网络"按钮
- [ ] 阅读进度条正常显示
- [ ] 支持 `progress` 属性

### 4.4 Footer 验收

- [ ] `home` 变体：浅色背景，二维码，联系方式
- [ ] `article` 变体：深色背景，简洁链接
- [ ] 支持 `variant` 属性切换

---

## 5. 实现步骤

### 5.1 NoiseTexture 组件

```typescript
// components/layout/NoiseTexture.tsx
import styles from './NoiseTexture.module.css';

interface NoiseTextureProps {
  opacity?: number;
}

export function NoiseTexture({ opacity = 0.05 }: NoiseTextureProps) {
  return (
    <div
      className={styles.noiseTexture}
      style={{ opacity }}
    />
  );
}
```

```css
/* components/layout/NoiseTexture.module.css */
.noiseTexture {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: var(--z-noise);
  background: url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)"/%3E%3C/svg%3E');
}
```

### 5.2 GridLines 组件

```typescript
// components/layout/GridLines.tsx
import styles from './GridLines.module.css';

interface GridLinesProps {
  columns?: number;
}

export function GridLines({ columns = 12 }: GridLinesProps) {
  return (
    <div className={styles.gridLines}>
      {Array.from({ length: columns }).map((_, i) => (
        <div key={i} className={styles.line} />
      ))}
    </div>
  );
}
```

### 5.3 Header 组件

```typescript
// components/layout/Header.tsx
'use client';

import Link from 'next/link';
import styles from './Header.module.css';

interface HeaderProps {
  progress?: number;
}

export function Header({ progress = 0 }: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Link href="/" className={styles.backLink}>
          <i className="ri-arrow-left-line" />
          <div className={styles.logoIcon}>
            <div className={styles.logoInner} />
          </div>
          <span>Back</span>
        </Link>
      </div>

      <div className={styles.logo}>ToWow</div>

      <div className={styles.right}>
        <button className={styles.btnOutline}>加入网络</button>
      </div>

      <div
        className={styles.progressBar}
        style={{ width: `${progress}%` }}
      />
    </header>
  );
}
```

### 5.4 Footer 组件

```typescript
// components/layout/Footer.tsx
import styles from './Footer.module.css';

interface FooterProps {
  variant: 'home' | 'article';
}

export function Footer({ variant }: FooterProps) {
  if (variant === 'article') {
    return <ArticleFooter />;
  }
  return <HomeFooter />;
}

function HomeFooter() {
  // 首页 Footer 实现
}

function ArticleFooter() {
  // 文章页 Footer 实现
}
```

---

## 6. 依赖关系

### 6.1 硬依赖

- TASK-NEXTJS-002: CSS 变量系统（需要 CSS 变量）

### 6.2 接口依赖

- TASK-NEXTJS-003: 字体配置
- TASK-NEXTJS-004: 动画系统

### 6.3 被依赖

- TASK-NEXTJS-007: 首页组件
- TASK-NEXTJS-008: 文章组件

---

## 7. 技术说明

### 7.1 Server Component vs Client Component

| 组件 | 类型 | 原因 |
|------|------|------|
| NoiseTexture | Server | 纯展示，无交互 |
| GridLines | Server | 纯展示，无交互 |
| Header | Client | 需要读取滚动位置更新进度条 |
| Footer | Server | 纯展示，无交互 |

### 7.2 CSS Modules 命名规范

- 使用 camelCase：`noiseTexture`、`gridLines`
- 避免使用 BEM 命名（CSS Modules 已提供作用域隔离）

---

## 8. 注意事项

- Header 的进度条需要在页面级别计算滚动进度
- Footer 的两种变体样式差异较大，注意代码复用
- 确保 Remix Icon CDN 已在 layout.tsx 中引入
- 测试时注意 z-index 层级是否正确
