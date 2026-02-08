# TASK-EXP-011: 动画与交互优化

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-011 |
| 状态 | TODO |
| 优先级 | P2 |
| 预估工时 | 3h |
| Beads ID | `towow-bg4` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

优化页面动画效果和交互体验，提升产品质感。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 附录 B CSS 变量扩展
- TASK-EXP-009 集成后的页面
- 现有设计规范

## 3. 输出

- 动画效果增强
- 交互反馈优化
- 加载状态优化

## 4. 验收标准

- [ ] 消息入场动画流畅
- [ ] 状态切换过渡动画
- [ ] 按钮点击反馈
- [ ] 加载状态动画（脉冲/骨架屏）
- [ ] 滚动行为优化
- [ ] 协商进行中的进度指示
- [ ] 无性能问题（60fps）
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：
- TASK-EXP-009（页面集成与状态管理）

**接口依赖**：无

## 6. 实现要点

```css
/* 动画变量 */
:root {
  --animation-message-in: slideInUp 0.3s ease-out;
  --animation-pulse: pulse 2s infinite;
  --animation-fade-in: fadeIn 0.2s ease-out;
  --transition-default: all 0.2s ease;
}

/* 消息入场动画 */
@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 脉冲动画 */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 状态指示器动画 */
.statusIndicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.statusIndicator.inProgress::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-processing);
  animation: var(--animation-pulse);
}

/* 骨架屏 */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-surface) 25%,
    var(--color-muted) 50%,
    var(--color-surface) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
```

```typescript
// 进度指示组件
function NegotiationProgress({ status }: { status: NegotiationStatus }) {
  const steps = ['等待开始', '协商中', '已完成'];
  const currentStep = status === 'waiting' ? 0 : status === 'in_progress' ? 1 : 2;

  return (
    <div className={styles.progress}>
      {steps.map((step, index) => (
        <div
          key={step}
          className={cn(
            styles.step,
            index <= currentStep && styles.active,
            index === currentStep && styles.current
          )}
        >
          <span className={styles.dot} />
          <span className={styles.label}>{step}</span>
        </div>
      ))}
    </div>
  );
}
```

## 7. 测试要点

- 动画流畅度测试（Chrome DevTools Performance）
- 各状态过渡测试
- 加载状态测试
- 移动端性能测试

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
