# TASK-NEXTJS-006: UI 原子组件

## 任务元信息

- **任务 ID**: TASK-NEXTJS-006
- **Beads ID**: `towow-13g`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 4 小时
- **状态**: TODO

---

## 1. 目标

实现所有 UI 原子组件，包括 Button、ContentCard、Shape、LinkArrow、NodeItem、QuoteBlock、Divider。

---

## 2. 输入

- `ToWow - 几何花园 V1.html` 第 125-192 行（Button, ContentCard, Shape）
- `ToWow - 几何花园 V1.html` 第 64-76 行（LinkArrow）
- `ToWow - 几何花园 V1.html` 第 253-282 行（NodeItem）
- `从注意力到价值 - ToWow深度阅读.html` 第 373-409 行（QuoteBlock, Divider）
- TECH-NEXTJS-MIGRATION-v5.md 第 4.4 节的接口契约

---

## 3. 输出

- `components/ui/Button.tsx` + `.module.css`
- `components/ui/ContentCard.tsx` + `.module.css`
- `components/ui/Shape.tsx` + `.module.css`
- `components/ui/LinkArrow.tsx` + `.module.css`
- `components/ui/NodeItem.tsx` + `.module.css`
- `components/ui/QuoteBlock.tsx` + `.module.css`
- `components/ui/Divider.tsx` + `.module.css`

---

## 4. 验收标准

### 4.1 Button 验收

- [ ] `primary` 变体：黑底白字
- [ ] `outline` 变体：透明底黑边
- [ ] hover 时背景变紫色（::after 动画）
- [ ] 支持 `href` 属性（渲染为 Link）
- [ ] 支持 `onClick` 属性（渲染为 button）

### 4.2 ContentCard 验收

- [ ] 毛玻璃效果 `backdrop-filter: blur(8px)`
- [ ] 半透明白色背景
- [ ] hover 时上移 5px
- [ ] 圆角 4px

### 4.3 Shape 验收

- [ ] 支持 `circle`、`square`、`triangle` 三种类型
- [ ] 支持 `size`、`color`、`position` 属性
- [ ] 支持 `animation`、`opacity`、`blur`、`rotate` 属性
- [ ] 支持 `border` 属性（空心图形）
- [ ] 支持 `mixBlendMode` 属性
- [ ] triangle 使用 border 技巧正确实现

### 4.4 LinkArrow 验收

- [ ] 包含右箭头图标
- [ ] hover 时下划线出现
- [ ] hover 时箭头右移

### 4.5 NodeItem 验收

- [ ] 圆形/方形节点
- [ ] 包含图标和标签
- [ ] hover 时放大 1.15 倍

### 4.6 QuoteBlock 验收

- [ ] 左边框 6px 紫色
- [ ] 背景 sage green
- [ ] 左上角引号图标

### 4.7 Divider 验收

- [ ] 三个小图形：圆形（紫）、方形（绿）、三角形（杏）
- [ ] 居中排列，间距 15px

---

## 5. 实现步骤

### 5.1 Button 组件

```typescript
// components/ui/Button.tsx
import Link from 'next/link';
import styles from './Button.module.css';

interface ButtonProps {
  variant: 'primary' | 'outline';
  children: React.ReactNode;
  href?: string;
  onClick?: () => void;
  className?: string;
}

export function Button({ variant, children, href, onClick, className }: ButtonProps) {
  const buttonClass = `${styles.btn} ${styles[variant]} ${className || ''}`;

  if (href) {
    return (
      <Link href={href} className={buttonClass}>
        {children}
      </Link>
    );
  }

  return (
    <button className={buttonClass} onClick={onClick}>
      {children}
    </button>
  );
}
```

```css
/* components/ui/Button.module.css */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 18px 42px;
  font-size: 18px;
  font-family: var(--f-cn-head);
  cursor: pointer;
  transition: var(--transition-slow);
  position: relative;
  overflow: hidden;
  text-decoration: none;
  z-index: 10;
}

.btn::after {
  content: '';
  position: absolute;
  width: 0%;
  height: 100%;
  top: 0;
  left: 0;
  background: var(--c-primary);
  z-index: -1;
  transition: width var(--transition-normal);
}

.btn:hover::after {
  width: 100%;
}

.primary {
  background: #000;
  color: #fff;
  border: 1px solid #000;
}

.primary:hover {
  color: #000;
  border-color: var(--c-primary);
}

.outline {
  background: transparent;
  color: #000;
  border: 1px solid #000;
}

.outline:hover {
  border-color: var(--c-primary);
}
```

### 5.2 Shape 组件

```typescript
// components/ui/Shape.tsx
import styles from './Shape.module.css';

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
  border?: string;
}

export function Shape({
  type,
  size,
  color,
  position = {},
  animation,
  animationDuration,
  animationDelay,
  opacity = 1,
  blur,
  rotate,
  mixBlendMode,
  border,
}: ShapeProps) {
  const baseStyle: React.CSSProperties = {
    position: 'absolute',
    ...position,
    opacity,
    filter: blur ? `blur(${blur}px)` : undefined,
    transform: rotate ? `rotate(${rotate}deg)` : undefined,
    mixBlendMode: mixBlendMode as any,
    animationDuration,
    animationDelay,
  };

  if (type === 'triangle') {
    return (
      <div
        className={`${styles.shape} ${animation ? styles[animation] : ''}`}
        style={{
          ...baseStyle,
          width: 0,
          height: 0,
          borderLeft: `${size / 2}px solid transparent`,
          borderRight: `${size / 2}px solid transparent`,
          borderBottom: `${size * 0.866}px solid ${color}`,
        }}
      />
    );
  }

  return (
    <div
      className={`${styles.shape} ${styles[type]} ${animation ? styles[animation] : ''}`}
      style={{
        ...baseStyle,
        width: size,
        height: size,
        backgroundColor: border ? 'transparent' : color,
        border: border || undefined,
      }}
    />
  );
}
```

### 5.3 其他组件

按照 TECH 文档的接口契约实现 ContentCard、LinkArrow、NodeItem、QuoteBlock、Divider。

---

## 6. 依赖关系

### 6.1 硬依赖

- TASK-NEXTJS-002: CSS 变量系统

### 6.2 接口依赖

- TASK-NEXTJS-004: 动画系统

### 6.3 被依赖

- TASK-NEXTJS-007: 首页组件
- TASK-NEXTJS-008: 文章组件

---

## 7. 技术说明

### 7.1 组件类型

| 组件 | 类型 | 原因 |
|------|------|------|
| Button | Server | 可以是 Link 或 button |
| ContentCard | Server | 纯展示 |
| Shape | Server | 纯展示 |
| LinkArrow | Server | 纯展示 |
| NodeItem | Server | 纯展示 |
| QuoteBlock | Server | 纯展示 |
| Divider | Server | 纯展示 |

### 7.2 Triangle 实现原理

使用 CSS border 技巧：
- 设置 `width: 0; height: 0`
- 左右 border 透明
- 底部 border 有颜色
- 形成等腰三角形

---

## 8. 注意事项

- Button 的 ::after 动画需要 `overflow: hidden` 配合
- Shape 的 position 属性需要父元素有 `position: relative`
- 确保所有颜色使用 CSS 变量
- 测试所有 hover 效果
