# TASK-EXP-007: AgentAvatar 组件

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-007 |
| 状态 | TODO |
| 优先级 | P1 |
| 预估工时 | 1h |
| Beads ID | `towow-kdu` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

实现 Agent 头像组件，用于展示 Agent 的头像或首字母。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 5.1.5 节 AgentAvatar 设计

## 3. 输出

- `/components/experience/AgentAvatar.tsx` - Agent 头像组件
- `/components/experience/AgentAvatar.module.css` - 样式文件

## 4. 验收标准

- [ ] 支持三种尺寸（sm/md/lg）
- [ ] 有头像 URL 时显示图片
- [ ] 无头像时显示名称首字母
- [ ] 可选显示名称
- [ ] 样式符合设计规范
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：无

**接口依赖**：无

## 6. 实现要点

```typescript
// components/experience/AgentAvatar.tsx
interface AgentAvatarProps {
  agentId: string;
  name: string;
  avatarUrl?: string;
  size?: 'sm' | 'md' | 'lg';
  showName?: boolean;
}

const sizeMap = {
  sm: 24,
  md: 32,
  lg: 48,
};

export function AgentAvatar({
  agentId,
  name,
  avatarUrl,
  size = 'md',
  showName = false,
}: AgentAvatarProps) {
  const initial = name.charAt(0).toUpperCase();
  const dimension = sizeMap[size];

  return (
    <div className={styles.container}>
      <div
        className={cn(styles.avatar, styles[size])}
        style={{ width: dimension, height: dimension }}
      >
        {avatarUrl ? (
          <img src={avatarUrl} alt={name} />
        ) : (
          <span className={styles.initial}>{initial}</span>
        )}
      </div>
      {showName && <span className={styles.name}>{name}</span>}
    </div>
  );
}
```

```css
/* AgentAvatar.module.css */
.avatar {
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-weight: 600;
  overflow: hidden;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sm { font-size: 12px; }
.md { font-size: 14px; }
.lg { font-size: 18px; }
```

## 7. 测试要点

- 有头像 URL 渲染测试
- 无头像首字母渲染测试
- 三种尺寸渲染测试
- 显示名称测试

---

## 实现记录

> 开发完成后填写

### 实现说明

（待填写）

### 测试结果

（待填写）

### 变更记录

| 时间 | 变更内容 | 变更人 |
|------|----------|--------|
| 2026-01-29 | 创建任务 | proj |
