# TASK-EXP-008: NegotiationTimeline 组件

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-008 |
| 状态 | TODO |
| 优先级 | P0 |
| 预估工时 | 4h |
| Beads ID | `towow-ns6` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

实现协商时间线组件，展示协商过程中的消息流和状态。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 5.1.3 节 NegotiationTimeline 设计
- TASK-EXP-005 提供的 WebSocket Hook
- TASK-EXP-006 提供的 MessageBubble 组件

## 3. 输出

- `/components/experience/NegotiationTimeline.tsx` - 协商时间线组件
- `/components/experience/NegotiationTimeline.module.css` - 样式文件

## 4. 验收标准

- [ ] 时间线展示消息列表
- [ ] 自动滚动到最新消息
- [ ] 状态指示器（waiting/in_progress/completed/failed）
- [ ] 消息入场动画效果
- [ ] loading 状态支持
- [ ] 空状态展示
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：
- TASK-EXP-005（WebSocket Hook）- 需要消息数据
- TASK-EXP-006（MessageBubble 组件）- 需要消息渲染

**接口依赖**：无

## 6. 实现要点

```typescript
// components/experience/NegotiationTimeline.tsx
interface NegotiationTimelineProps {
  messages: NegotiationMessage[];
  status: NegotiationStatus;
  isLoading?: boolean;
  currentUserId?: string;
}

type NegotiationStatus = 'waiting' | 'in_progress' | 'completed' | 'failed';

export function NegotiationTimeline({
  messages,
  status,
  isLoading,
  currentUserId,
}: NegotiationTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className={styles.timeline}>
      <StatusIndicator status={status} />
      <div ref={containerRef} className={styles.messageList}>
        {messages.length === 0 && !isLoading && (
          <div className={styles.empty}>等待协商开始...</div>
        )}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.message_id}
            message={msg}
            isCurrentUser={msg.sender_id === currentUserId}
          />
        ))}
        {isLoading && <LoadingIndicator />}
      </div>
    </div>
  );
}
```

```css
/* NegotiationTimeline.module.css */
.timeline {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.messageList {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
}

.messageList > * {
  animation: var(--animation-message-in);
}

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
```

## 7. 测试要点

- 消息列表渲染测试
- 自动滚动测试
- 状态指示器测试
- 空状态测试
- loading 状态测试
- 消息动画测试

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
