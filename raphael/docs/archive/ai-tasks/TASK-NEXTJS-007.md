# TASK-NEXTJS-007: 首页组件

## 任务元信息

- **任务 ID**: TASK-NEXTJS-007
- **Beads ID**: `towow-0cg`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 4 小时
- **状态**: TODO

---

## 1. 目标

实现首页专用组件，包括 Hero、ContentSection、NetworkJoin。

---

## 2. 输入

- `ToWow - 几何花园 V1.html` 第 201-239 行（Hero）
- `ToWow - 几何花园 V1.html` 第 351-480 行（ContentSection 的 6 个实例）
- `ToWow - 几何花园 V1.html` 第 483-529 行（NetworkJoin）
- TECH-NEXTJS-MIGRATION-v5.md 第 4.2 节的接口契约

---

## 3. 输出

- `components/home/Hero.tsx` + `.module.css`
- `components/home/ContentSection.tsx` + `.module.css`
- `components/home/NetworkJoin.tsx` + `.module.css`

---

## 4. 验收标准

### 4.1 Hero 验收

- [ ] 全屏高度 `100vh`
- [ ] 标题居中显示
- [ ] 副标题样式正确
- [ ] 两个按钮（primary + outline）
- [ ] 背景动画：紫色圆形 + 绿色方形
- [ ] `growUp` 动画正常播放

### 4.2 ContentSection 验收

- [ ] 支持 `gridColumn` 属性控制位置
- [ ] 使用 ContentCard 组件
- [ ] 标题支持 HTML（换行）
- [ ] 内容支持 HTML（换行）
- [ ] LinkArrow 链接正常
- [ ] 支持 children 放置几何装饰

### 4.3 NetworkJoin 验收

- [ ] SVG 连接线正确显示
- [ ] 中心 ToWow 节点
- [ ] 5 个浮动节点位置正确
- [ ] 各节点 float 动画延迟不同
- [ ] hover 效果正常

---

## 5. 实现步骤

### 5.1 Hero 组件

```typescript
// components/home/Hero.tsx
import { Button } from '@/components/ui/Button';
import styles from './Hero.module.css';

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

export function Hero({
  title,
  subtitle,
  primaryAction,
  secondaryAction,
}: HeroProps) {
  return (
    <section className={styles.hero}>
      {/* 背景动画 */}
      <div className={styles.bgAnim}>
        <div className={styles.circle} />
        <div className={styles.square} />
      </div>

      {/* 内容 */}
      <div className={styles.gridWrapper}>
        <div className={styles.content}>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.subtitle}>{subtitle}</p>
          <div className={styles.actions}>
            <Button variant="outline" href={secondaryAction.href}>
              {secondaryAction.label}
            </Button>
            <Button variant="primary" href={primaryAction.href}>
              {primaryAction.label}
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
```

```css
/* components/home/Hero.module.css */
.hero {
  height: 100vh;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  position: relative;
}

.bgAnim {
  position: absolute;
  bottom: -100px;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  height: 100%;
  z-index: 1;
  pointer-events: none;
}

.circle {
  position: absolute;
  bottom: -10%;
  left: 30%;
  width: 600px;
  height: 600px;
  background: var(--c-primary);
  border-radius: 50%;
  opacity: 0.6;
  animation: growUp 1.5s ease-out forwards;
  filter: blur(20px);
}

.square {
  position: absolute;
  bottom: -5%;
  right: 30%;
  width: 400px;
  height: 400px;
  background: var(--c-secondary);
  opacity: 0.6;
  animation: growUp 1.8s ease-out forwards 0.3s;
  mix-blend-mode: multiply;
}

.gridWrapper {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  column-gap: var(--grid-gap);
  width: var(--container-width);
  margin: 0 auto;
  position: relative;
  z-index: 2;
  align-items: center;
}

.content {
  grid-column: 3 / 11;
  z-index: 10;
  position: relative;
}

.title {
  font-size: 66px;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: #000;
}

.subtitle {
  text-align: center;
  margin-top: 32px;
  font-size: 22px;
  max-width: 860px;
  margin-left: auto;
  margin-right: auto;
  color: #444;
}

.actions {
  margin-top: 56px;
  display: flex;
  gap: 24px;
  justify-content: center;
}
```

### 5.2 ContentSection 组件

```typescript
// components/home/ContentSection.tsx
import { ContentCard } from '@/components/ui/ContentCard';
import { LinkArrow } from '@/components/ui/LinkArrow';
import styles from './ContentSection.module.css';

interface ContentSectionProps {
  title: string;
  content: string;
  linkText: string;
  linkHref: string;
  gridColumn: string;
  children?: React.ReactNode;
}

export function ContentSection({
  title,
  content,
  linkText,
  linkHref,
  gridColumn,
  children,
}: ContentSectionProps) {
  return (
    <section className={styles.section}>
      {/* 几何装饰 */}
      {children}

      {/* 内容卡片 */}
      <div className={styles.gridWrapper}>
        <div style={{ gridColumn }}>
          <ContentCard>
            <h2
              className={styles.title}
              dangerouslySetInnerHTML={{ __html: title }}
            />
            <p
              className={styles.body}
              dangerouslySetInnerHTML={{ __html: content }}
            />
            <LinkArrow href={linkHref}>{linkText}</LinkArrow>
          </ContentCard>
        </div>
      </div>
    </section>
  );
}
```

### 5.3 NetworkJoin 组件

```typescript
// components/home/NetworkJoin.tsx
import { NodeItem } from '@/components/ui/NodeItem';
import styles from './NetworkJoin.module.css';

interface NetworkNode {
  id: string;
  icon: string;
  label: string;
  color: string;
  position: {
    top?: string;
    left?: string;
    right?: string;
  };
  animationDelay?: string;
  isSquare?: boolean;
}

interface NetworkJoinProps {
  nodes: NetworkNode[];
}

export function NetworkJoin({ nodes }: NetworkJoinProps) {
  return (
    <section className={styles.section}>
      <div className={styles.gridWrapper}>
        {/* SVG 连接线 */}
        <svg className={styles.lines}>
          <line x1="50%" y1="85%" x2="20%" y2="30%" />
          <line x1="50%" y1="85%" x2="35%" y2="20%" />
          <line x1="50%" y1="85%" x2="65%" y2="25%" />
          <line x1="50%" y1="85%" x2="80%" y2="35%" />
          <line x1="50%" y1="85%" x2="50%" y2="15%" />
        </svg>

        {/* 中心节点 */}
        <div className={styles.centerNode}>
          <div className={styles.centerBox}>ToWow</div>
          <h2 className={styles.centerTitle}>加入网络</h2>
          <p className={styles.centerDesc}>
            网络的价值来自节点的多样性。<br />
            无论你是什么身份，都有参与的方式。
          </p>
        </div>

        {/* 浮动节点 */}
        <div className={styles.floatingNodes}>
          {nodes.map((node) => (
            <div
              key={node.id}
              className={styles.nodeWrapper}
              style={{
                ...node.position,
                animationDelay: node.animationDelay,
              }}
            >
              <NodeItem
                icon={node.icon}
                label={node.label}
                color={node.color}
                isSquare={node.isSquare}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

---

## 6. 依赖关系

### 6.1 硬依赖

- TASK-NEXTJS-005: 布局组件（GridWrapper 样式）
- TASK-NEXTJS-006: UI 原子组件（Button, ContentCard, LinkArrow, NodeItem, Shape）

### 6.2 接口依赖

无

### 6.3 被依赖

- TASK-NEXTJS-009: 首页集成

---

## 7. 技术说明

### 7.1 组件类型

| 组件 | 类型 | 原因 |
|------|------|------|
| Hero | Server | 纯展示，无交互 |
| ContentSection | Server | 纯展示，无交互 |
| NetworkJoin | Server | 纯展示，无交互 |

### 7.2 dangerouslySetInnerHTML 使用

- 用于支持标题和内容中的 `<br>` 换行
- 数据来源是静态配置，无 XSS 风险
- 如果后续需要动态内容，需要做 sanitize

### 7.3 SVG 连接线

- 使用百分比定位，适应不同容器大小
- `stroke-dasharray="5,5"` 实现虚线效果

---

## 8. 注意事项

- Hero 的 growUp 动画需要 `animation-fill-mode: forwards`
- ContentSection 的 gridColumn 需要与原 HTML 完全一致
- NetworkJoin 的节点位置需要精确匹配原 HTML
- 测试时注意各 section 之间的间距
