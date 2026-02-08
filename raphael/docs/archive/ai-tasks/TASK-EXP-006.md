# TASK-EXP-006: MessageBubble 组件

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-006 |
| 状态 | TODO |
| 优先级 | P1 |
| 预估工时 | 2h |
| Beads ID | `towow-uk3` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

实现消息气泡组件，用于展示协商过程中的消息。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 5.1.4 节 MessageBubble 设计
- TECH-PRODUCT-PAGE-v5.md 附录 B CSS 变量扩展

## 3. 输出

- `/components/experience/MessageBubble.tsx` - 消息气泡组件
- `/components/experience/MessageBubble.module.css` - 样式文件

## 4. 验收标准

- [ ] 支持三种消息类型样式（text/system/action）
- [ ] 显示发送者头像和名称
- [ ] 显示时间戳
- [ ] 区分当前用户消息和其他 Agent 消息
- [ ] 样式符合设计规范（使用 CSS Variables）
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：无

**接口依赖**：无

## 6. 实现要点

```typescript
// components/experience/MessageBubble.tsx
interface MessageBubbleProps {
  message: NegotiationMessage;
  isCurrentUser?: boolean;
}

export function MessageBubble({ message, isCurrentUser }: MessageBubbleProps) {
  const bubbleClass = cn(
    styles.bubble,
    styles[message.message_type],
    isCurrentUser && styles.currentUser
  );

  return (
    <div className={bubbleClass}>
      <div className={styles.header}>
        <AgentAvatar
          agentId={message.sender_id}
          name={message.sender_name}
          size="sm"
        />
        <span className={styles.name}>{message.sender_name}</span>
        <span className={styles.time}>
          {formatTime(message.timestamp)}
        </span>
      </div>
      <div className={styles.content}>{message.content}</div>
    </div>
  );
}
```

```css
/* MessageBubble.module.css */
.bubble {
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
}

.text {
  background: var(--bubble-agent-bg);
}

.system {
  background: var(--bubble-system-bg);
  text-align: center;
}

.action {
  background: var(--bubble-agent-bg);
  border-left: 3px solid var(--color-primary);
}

.currentUser {
  background: var(--bubble-user-bg);
}
```

## 7. 测试要点

- text 类型消息渲染测试
- system 类型消息渲染测试
- action 类型消息渲染测试
- 当前用户消息样式测试
- 时间戳格式化测试

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
